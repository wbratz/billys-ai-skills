#!/usr/bin/env python3
"""
rlm_plan.py — produce a plan for an RLM run without executing it.

Inspects the target, classifies it, recommends a mode, computes estimated
cost/fanout, and emits both human-readable text and JSON.

Usage:
  python rlm_plan.py --target <path|url> --prompt "<question>" [--mode auto|min|default|max]
                     [--max-bytes N] [--no-color]

Output:
  Markdown plan to stdout (human-readable).
  JSON appended as a fenced block at the end (machine-readable).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

MODE_CONFIGS = {
    "min": {
        "max_depth": 1,
        "max_iterations": 6,
        "max_timeout": 120,
        "max_errors": 2,
        "max_concurrent_subcalls": 4,
        "root_model": "claude-sonnet-4-6",
        "depth1_model": None,
        "depth2_model": None,
        "llm_query_model": "claude-haiku-4-5-20251001",
    },
    "default": {
        "max_depth": 2,
        "max_iterations": 12,
        "max_timeout": 300,
        "max_errors": 4,
        "max_concurrent_subcalls": 8,
        "root_model": "claude-opus-4-7",
        "depth1_model": "claude-sonnet-4-6",
        "depth2_model": None,
        "llm_query_model": "claude-haiku-4-5-20251001",
    },
    "max": {
        "max_depth": 3,
        "max_iterations": 20,
        "max_timeout": 900,
        "max_errors": 6,
        "max_concurrent_subcalls": 12,
        "root_model": "claude-opus-4-7",
        "depth1_model": "claude-sonnet-4-6",
        "depth2_model": "claude-haiku-4-5-20251001",
        "llm_query_model": "claude-haiku-4-5-20251001",
    },
}

COST_PER_MTOK = {
    "claude-opus-4-7": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
}

CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c",
              ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".kt", ".scala"}
TEXT_EXTS = {".txt", ".md", ".rst", ".org", ".tex"}
DOC_EXTS = {".pdf", ".docx", ".doc", ".rtf", ".odt"}
LOG_EXTS = {".log", ".jsonl", ".ndjson"}
TABULAR_EXTS = {".csv", ".tsv", ".parquet"}
NOTEBOOK_EXTS = {".ipynb"}
MARKUP_EXTS = {".html", ".htm", ".xml"}

IGNORE_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache",
                "dist", "build", "target", ".next", ".nuxt", ".idea", ".vscode"}

SECRET_PATTERNS = [
    (re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}"), "Anthropic API key"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "OpenAI-style API key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub PAT"),
    (re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"), "PEM private key"),
]

DECOMPOSITION_KEYWORDS = [
    "compare across", "audit", "review every", "trace dependenc",
    "find all places", "exhaustively", "for each", "every file",
]


def classify_target(target: str) -> dict:
    if target.startswith(("http://", "https://")):
        return {
            "target_type": "url",
            "target_repr": target,
            "size_bytes": 0,
            "file_count": 1,
            "files_by_type": {"url": 1},
            "warnings": ["URL size unknown until fetched"],
        }

    p = Path(target)
    if not p.exists():
        if any(c in target for c in "*?["):
            matches = list(Path(".").glob(target))
            if matches:
                return _classify_files(matches, f"glob:{target}")
        return {
            "target_type": "missing",
            "target_repr": target,
            "size_bytes": 0,
            "file_count": 0,
            "files_by_type": {},
            "warnings": [f"Target not found: {target}"],
        }

    if p.is_file():
        return _classify_files([p], str(p))
    if p.is_dir():
        return _classify_dir(p)
    return {
        "target_type": "unknown",
        "target_repr": str(p),
        "size_bytes": 0,
        "file_count": 0,
        "files_by_type": {},
        "warnings": ["Target is neither file nor directory"],
    }


def _ext_type(ext: str) -> str:
    ext = ext.lower()
    if ext in DOC_EXTS:
        return "pdf" if ext == ".pdf" else "document"
    if ext in TEXT_EXTS:
        return "text"
    if ext in LOG_EXTS:
        return "log"
    if ext in TABULAR_EXTS:
        return "tabular"
    if ext in NOTEBOOK_EXTS:
        return "notebook"
    if ext in CODE_EXTS:
        return "code"
    if ext in MARKUP_EXTS:
        return "markup"
    return "other"


def _classify_files(paths: list[Path], repr_str: str) -> dict:
    files_by_type: dict[str, int] = {}
    total_bytes = 0
    warnings = []
    for p in paths:
        try:
            sz = p.stat().st_size
        except OSError as exc:
            warnings.append(f"stat failed: {p}: {exc}")
            continue
        total_bytes += sz
        t = _ext_type(p.suffix)
        files_by_type[t] = files_by_type.get(t, 0) + 1

    if len(paths) == 1:
        target_type = _ext_type(paths[0].suffix)
    else:
        target_type = "multi-file"

    return {
        "target_type": target_type,
        "target_repr": repr_str,
        "size_bytes": total_bytes,
        "file_count": len(paths),
        "files_by_type": files_by_type,
        "warnings": warnings,
    }


def _classify_dir(root: Path) -> dict:
    files_by_type: dict[str, int] = {}
    total_bytes = 0
    file_count = 0
    warnings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            try:
                sz = p.stat().st_size
            except OSError:
                continue
            t = _ext_type(p.suffix)
            if t == "other" and sz > 256 * 1024:
                continue
            files_by_type[t] = files_by_type.get(t, 0) + 1
            total_bytes += sz
            file_count += 1
    if file_count > 1000:
        warnings.append(f"Large directory: {file_count} files. Consider --max-bytes.")
    return {
        "target_type": "dir",
        "target_repr": str(root),
        "size_bytes": total_bytes,
        "file_count": file_count,
        "files_by_type": files_by_type,
        "warnings": warnings,
    }


def recommend_mode(classification: dict, prompt: str) -> tuple[str, list[str]]:
    reasons = []
    size = classification["size_bytes"]
    files = classification["file_count"]
    ttype = classification["target_type"]

    prompt_lower = prompt.lower()
    has_decomp = any(kw in prompt_lower for kw in DECOMPOSITION_KEYWORDS)

    if ttype == "url" and files == 1:
        reasons.append("single URL")
        mode = "min"
    elif size < 50 * 1024 and files <= 5:
        reasons.append("tiny target")
        mode = "min"
    elif size > 50 * 1024 * 1024 or files > 500:
        reasons.append("very large target")
        mode = "max"
    else:
        reasons.append("medium-size target")
        mode = "default"

    if has_decomp:
        if mode == "min":
            reasons.append("prompt contains decomposition keyword; bumping min->default")
            mode = "default"
        elif mode == "default":
            reasons.append("prompt contains decomposition keyword; bumping default->max")
            mode = "max"

    return mode, reasons


def estimate_tokens(size_bytes: int, files_by_type: dict) -> int:
    if not size_bytes:
        return 0
    code_bytes = 0
    for t, count in files_by_type.items():
        if t == "code":
            code_bytes = (size_bytes * count) // max(sum(files_by_type.values()), 1)
    code_ratio = code_bytes / size_bytes if size_bytes else 0
    bpt = 3.5 * code_ratio + 4 * (1 - code_ratio)
    return int(size_bytes / bpt) if bpt else size_bytes // 4


def predict_fanout(est_tokens: int, mode: str) -> tuple[int, int]:
    if est_tokens <= 0:
        return 0, 0
    chunk_size_tokens = 4000
    chunks = max(1, (est_tokens + chunk_size_tokens - 1) // chunk_size_tokens)
    conc = MODE_CONFIGS[mode]["max_concurrent_subcalls"]
    rounds = max(1, (chunks + conc - 1) // conc)
    return chunks, rounds


def estimate_cost(est_tokens: int, fanout: int, mode: str) -> tuple[float, float]:
    cfg = MODE_CONFIGS[mode]
    iter_tokens_root = 8000 * cfg["max_iterations"]
    haiku_tokens = fanout * 4500
    sonnet_tokens = (fanout // 4) * 6000 if cfg["depth1_model"] else 0
    cost_low, cost_high = 0.0, 0.0
    for model_id, tokens in [
        (cfg["root_model"], iter_tokens_root),
        (cfg["depth1_model"], sonnet_tokens),
        (cfg["llm_query_model"], haiku_tokens),
    ]:
        if not model_id or tokens <= 0:
            continue
        lo, hi = COST_PER_MTOK.get(model_id, (1.0, 5.0))
        cost_low += (tokens / 1_000_000) * lo
        cost_high += (tokens / 1_000_000) * hi
    return cost_low, cost_high


def scan_secrets_quick(target: str) -> list[str]:
    p = Path(target)
    if not p.exists() or not p.is_file() or p.stat().st_size > 1024 * 1024:
        return []
    try:
        text = p.read_text(errors="replace")
    except Exception:
        return []
    hits = []
    for pat, label in SECRET_PATTERNS:
        if pat.search(text):
            hits.append(label)
    return hits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--mode", default="auto", choices=["auto", "min", "default", "max"])
    parser.add_argument("--max-bytes", type=int, default=None)
    args = parser.parse_args()

    classification = classify_target(args.target)
    if classification["target_type"] == "missing":
        print(json.dumps({"ok": False, "error": classification["warnings"][0]}))
        sys.exit(1)

    if args.mode == "auto":
        mode, reasons = recommend_mode(classification, args.prompt)
    else:
        mode = args.mode
        reasons = [f"user-specified mode={mode}"]

    cfg = MODE_CONFIGS[mode]
    est_tokens = estimate_tokens(classification["size_bytes"], classification["files_by_type"])
    chunks, rounds = predict_fanout(est_tokens, mode)
    cost_low, cost_high = estimate_cost(est_tokens, chunks, mode)
    secrets = scan_secrets_quick(args.target)
    plan_id = uuid.uuid4().hex[:8]

    plan = {
        "ok": True,
        "plan_id": plan_id,
        "target": classification,
        "prompt": args.prompt,
        "recommended_mode": mode,
        "reasons": reasons,
        "config": cfg,
        "est_tokens": est_tokens,
        "predicted_fanout": {"chunks": chunks, "rounds": rounds, "concurrency": cfg["max_concurrent_subcalls"]},
        "est_cost_usd": {"low": round(cost_low, 2), "high": round(cost_high, 2)},
        "secret_scan": {"hits": secrets},
        "log_path": f".rlm/logs/rlm-{plan_id}.jsonl",
        "requires_budget_flag": mode == "max",
    }

    # Human-readable plan
    print(f"## RLM Plan {plan_id}\n")
    print(f"**Target:** `{classification['target_repr']}` ({classification['target_type']})")
    if classification["size_bytes"]:
        kb = classification["size_bytes"] / 1024
        print(f"**Size:** {kb:,.1f} KB across {classification['file_count']} file(s), ~{est_tokens:,} tokens")
    print(f"**Question:** {args.prompt}\n")
    print(f"**Recommended mode:** `{mode}`  ({', '.join(reasons)})")
    print(f"  - max_depth={cfg['max_depth']}, max_iterations={cfg['max_iterations']}, "
          f"max_timeout={cfg['max_timeout']}s, max_errors={cfg['max_errors']}, "
          f"concurrency={cfg['max_concurrent_subcalls']}\n")
    print(f"**Model routing:**")
    print(f"  - Root (depth 0): `{cfg['root_model']}`")
    print(f"  - Depth 1:        `{cfg['depth1_model'] or '(none)'}`")
    print(f"  - Depth 2:        `{cfg['depth2_model'] or '(none)'}`")
    print(f"  - llm_query:      `{cfg['llm_query_model']}`\n")
    if chunks:
        print(f"**Predicted fanout:** ~{chunks} Haiku calls in {rounds} round(s) at {cfg['max_concurrent_subcalls']}-wide")
    print(f"**Est. cost:** ${cost_low:.2f} - ${cost_high:.2f}")
    print(f"**Trajectory log:** `{plan['log_path']}`")
    if secrets:
        print(f"\n**[WARN]** Possible secrets detected in target: {', '.join(secrets)}")
    for w in classification["warnings"]:
        print(f"**[WARN]** {w}")
    if mode == "max":
        print(f"\n**Note:** `max` mode requires `--max-budget=$N` at run time.")
    print(f"\nApprove? (yes / mode=<min|default|max> / cancel)")

    print("\n```json")
    print(json.dumps(plan, indent=2))
    print("```")


if __name__ == "__main__":
    main()
