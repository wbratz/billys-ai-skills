#!/usr/bin/env python3
"""
classify.py - shared RLM-signal detector used by hooks and skills.

Given a prompt (string) and an optional cwd, returns a structured verdict:

    {
      "verdict": "rlm" | "direct" | "ambiguous",
      "score": float,                # 0.0 - 1.0; higher = more RLM-shaped
      "signals": [{"kind": "...", "detail": "..."}, ...],
      "totals": {"size_bytes": N, "file_count": N, "url_count": N},
      "config_used": {...}
    }

The verdict is heuristic. It is intentionally conservative (favors "direct"
when in doubt) so misroutes cost the user nothing extra.

Stdlib-only. No external HTTP. Path stats are cheap and bounded.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

DEFAULTS_PATH = Path(__file__).parent.parent / "config" / "defaults.json"
USER_CONFIG_PATH = Path(os.path.expanduser("~")) / ".rlm" / "auto-config.json"

PATH_RE = re.compile(r"""(?xi)
    (?:                                # absolute or relative path
        [A-Za-z]:[\\/][^\s'"<>|]+      # Windows abs (C:\... or C:/...)
      | /[^\s'"<>|]+                   # Unix abs
      | \\[^\s'"<>|]+                  # root path copied with backslashes
      | \.[\\/][^\s'"<>|]+             # explicit relative (./... or .\...)
      | \.\.[\\/][^\s'"<>|]+           # parent relative
      | (?:[\w\-.]+[\\/]){1,}[\w\-.]+  # bare relative (foo/bar or foo\bar)
    )
""")
URL_RE = re.compile(r"https?://[^\s'\"<>]+", re.IGNORECASE)
GLOB_RE = re.compile(r"(?:\*\*?/|\*\.[a-zA-Z0-9]+|\?\.[a-zA-Z0-9]+|\[[^\]]+\])")

CORPUS_HINT_RE = re.compile(
    r"\b(corpus|repo|repository|codebase|directory|dataset|archive|"
    r"transcripts?|logs?|tickets?|recordings?|PDFs?|documents?)\b",
    re.IGNORECASE,
)


def load_config() -> dict:
    """Layered config: ship defaults, user override, env kill switch."""
    cfg = {}
    if DEFAULTS_PATH.is_file():
        try:
            cfg = json.loads(DEFAULTS_PATH.read_text())
        except Exception:
            cfg = {}
    if USER_CONFIG_PATH.is_file():
        try:
            cfg.update(json.loads(USER_CONFIG_PATH.read_text()))
        except Exception:
            pass
    kill = cfg.get("kill_switch_env", "RLM_AUTO_DISABLE")
    if os.environ.get(kill):
        cfg["enabled"] = False
    return cfg


def _path_size_bytes(p: Path, cap_bytes: int = 50_000_000) -> tuple[int, int]:
    """Return (total_bytes, file_count). Walks dirs up to cap_bytes worth."""
    if not p.exists():
        return 0, 0
    if p.is_file():
        try:
            return p.stat().st_size, 1
        except OSError:
            return 0, 0
    total, count = 0, 0
    IGNORE = {".git", "node_modules", ".venv", "venv", "__pycache__",
              ".pytest_cache", "dist", "build", "target"}
    for dp, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in IGNORE]
        for fn in files:
            try:
                sz = (Path(dp) / fn).stat().st_size
            except OSError:
                continue
            total += sz
            count += 1
            if total >= cap_bytes:
                return total, count
    return total, count


def _resolve_prompt_path(raw: str, base: Path) -> Path | None:
    """Resolve a prompt path, including foreign separator styles.

    Prompts are often copied between operating systems. A Windows-style
    backslash path should still identify an existing local path when the
    classifier runs on macOS or Linux, and vice versa.
    """
    candidates = [raw]
    if os.sep == "/" and "\\" in raw:
        candidates.append(raw.replace("\\", "/"))
    elif os.sep == "\\" and "/" in raw:
        candidates.append(raw.replace("/", "\\"))

    for candidate in dict.fromkeys(candidates):
        path = Path(candidate)
        if not path.is_absolute():
            path = base / path
        if path.exists():
            return path
    return None


def classify(prompt: str, cwd: str | None = None) -> dict:
    cfg = load_config()
    if not cfg.get("enabled", True):
        return {
            "verdict": "direct",
            "score": 0.0,
            "signals": [{"kind": "disabled", "detail": "rlm-auto is disabled"}],
            "totals": {"size_bytes": 0, "file_count": 0, "url_count": 0},
            "config_used": cfg,
        }

    base = Path(cwd) if cwd else Path.cwd()

    signals: list[dict] = []
    score = 0.0
    total_bytes = 0
    total_files = 0
    url_count = 0

    # 1. Paths mentioned in prompt -> stat them
    seen_paths: set[str] = set()
    for m in PATH_RE.finditer(prompt):
        raw = m.group().rstrip(",.;:)]}>'\"")
        if raw in seen_paths:
            continue
        seen_paths.add(raw)
        p = _resolve_prompt_path(raw, base)
        if p is None:
            continue
        sz, n = _path_size_bytes(p)
        total_bytes += sz
        total_files += n
        if p.is_dir():
            signals.append({"kind": "dir", "detail": f"{raw} = {sz//1024} KB, {n} files"})
            if sz >= cfg.get("min_size_bytes", 51200) or n >= cfg.get("min_file_count", 5):
                score += 0.6
        elif sz >= cfg.get("min_size_bytes", 51200):
            signals.append({"kind": "big_file", "detail": f"{raw} = {sz//1024} KB"})
            score += 0.6
        else:
            signals.append({"kind": "small_file", "detail": f"{raw} = {sz//1024} KB"})

    # 2. URLs
    urls = URL_RE.findall(prompt)
    url_count = len(urls)
    if url_count >= 3:
        signals.append({"kind": "many_urls", "detail": f"{url_count} URLs in prompt"})
        score += 0.5
    elif url_count == 1:
        signals.append({"kind": "url", "detail": urls[0][:80]})
        # one URL is rarely enough on its own
        score += 0.1

    # 3. Glob patterns
    globs = GLOB_RE.findall(prompt)
    if globs:
        signals.append({"kind": "glob", "detail": ", ".join(globs[:5])})
        score += 0.3

    # 4. Positive keywords
    prompt_lower = prompt.lower()
    pos_hits = [kw for kw in cfg.get("kw_positive", []) if kw.lower() in prompt_lower]
    if pos_hits:
        signals.append({"kind": "kw_positive", "detail": ", ".join(pos_hits[:5])})
        score += 0.15 * min(len(pos_hits), 3)

    # 5. Negative keywords (subtract)
    neg_hits = [kw for kw in cfg.get("kw_negative", []) if kw.lower() in prompt_lower]
    if neg_hits:
        signals.append({"kind": "kw_negative", "detail": ", ".join(neg_hits[:5])})
        score -= 0.4

    # 6. Corpus-shape nouns
    if CORPUS_HINT_RE.search(prompt):
        signals.append({"kind": "corpus_noun", "detail": "mentions corpus/repo/logs/etc."})
        score += 0.1

    score = max(0.0, min(1.0, score))

    # Verdict
    min_size = cfg.get("min_size_bytes", 51200)
    ambig = cfg.get("ambiguous_band", {})
    if score >= 0.5 and (total_bytes >= min_size or url_count >= 3 or total_files >= cfg.get("min_file_count", 5)):
        verdict = "rlm"
    elif score >= 0.35 or (total_bytes and ambig.get("size_bytes_low", 0) <= total_bytes < min_size):
        verdict = "ambiguous"
    else:
        verdict = "direct"

    return {
        "verdict": verdict,
        "score": round(score, 3),
        "signals": signals,
        "totals": {
            "size_bytes": total_bytes,
            "file_count": total_files,
            "url_count": url_count,
        },
        "config_used": {
            "min_size_bytes": cfg.get("min_size_bytes"),
            "min_file_count": cfg.get("min_file_count"),
            "auto_approve_cap_usd": cfg.get("auto_approve_cap_usd"),
        },
    }


def main() -> None:
    """CLI: read prompt from --prompt or stdin, print JSON verdict."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--cwd", default=None)
    args = ap.parse_args()
    prompt = args.prompt if args.prompt is not None else sys.stdin.read()
    result = classify(prompt, cwd=args.cwd)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
