#!/usr/bin/env python3
"""
rlm_native.py — Claude-Code-native fallback when the `rlms` package is unavailable.

This does NOT implement true RLM. It produces a structured "instructions for the host agent"
JSON that tells Claude Code how to simulate RLM using its own Agent/Task tooling:
chunk context, fan out sub-Agent calls for extraction, synthesize.

The host Claude reads this and orchestrates from there. Recursion is prompt-level only;
there is no Python REPL. This mode is clearly labeled in the output so users know
they're getting an approximation.

Usage:
  python rlm_native.py --target <path|url> --prompt "<question>" --mode <min|default|max>
                       [--log-dir .rlm/logs]
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

MODE_CONFIGS = {
    "min": {"max_chunks": 8, "concurrency": 4,
             "root_model": "claude-sonnet-4-6",
             "subagent_model": "claude-haiku-4-5-20251001"},
    "default": {"max_chunks": 32, "concurrency": 8,
                "root_model": "claude-opus-4-7",
                "subagent_model": "claude-haiku-4-5-20251001"},
    "max": {"max_chunks": 96, "concurrency": 12,
            "root_model": "claude-opus-4-7",
            "subagent_model": "claude-haiku-4-5-20251001"},
}


def chunk_text(text: str, target_chunk_tokens: int = 4000) -> list[str]:
    target_chars = target_chunk_tokens * 4
    chunks = []
    pos = 0
    while pos < len(text):
        end = min(pos + target_chars, len(text))
        if end < len(text):
            for sep in ("\n\n", "\n", ". "):
                back = text.rfind(sep, pos + target_chars // 2, end)
                if back != -1:
                    end = back + len(sep)
                    break
        chunks.append(text[pos:end])
        pos = end
    return chunks


def load_context_text(target: str, max_bytes: int | None) -> str:
    if target.startswith(("http://", "https://")):
        return f"[URL not fetched in native mode — paste content or install rlms: {target}]"
    p = Path(target)
    if not p.exists():
        return ""
    if p.is_file():
        try:
            data = p.read_text(errors="replace")
            if max_bytes and len(data) > max_bytes:
                data = data[:max_bytes]
            return data
        except Exception as exc:
            return f"[Failed to read {target}: {exc}]"
    if p.is_dir():
        parts = []
        total = 0
        cap = max_bytes or 2_000_000
        for fp in sorted(p.rglob("*")):
            if not fp.is_file():
                continue
            if any(x in fp.parts for x in (".git", "node_modules", ".venv", "__pycache__")):
                continue
            try:
                sub = fp.read_text(errors="replace")
            except Exception:
                continue
            chunk = f"\n\n=== {fp.relative_to(p)} ===\n{sub}"
            if total + len(chunk) > cap:
                break
            parts.append(chunk)
            total += len(chunk)
        return "".join(parts)
    return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--mode", default="default", choices=["min", "default", "max"])
    parser.add_argument("--max-bytes", type=int, default=None)
    parser.add_argument("--log-dir", default=".rlm/logs")
    parser.add_argument("--plan-id", default=None)
    args = parser.parse_args()

    cfg = MODE_CONFIGS[args.mode]
    text = load_context_text(args.target, args.max_bytes)
    if not text:
        print(json.dumps({"ok": False, "error": "No content loaded."}))
        sys.exit(1)

    chunks = chunk_text(text)[: cfg["max_chunks"]]
    plan_id = args.plan_id or uuid.uuid4().hex[:8]
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = log_dir / f"rlm-native-{plan_id}.chunks.json"
    chunks_path.write_text(json.dumps(chunks))

    instructions = {
        "ok": True,
        "mode_label": "claude-native-fallback",
        "warning": "rlms not installed — running in native fallback mode. "
                   "Recursion is prompt-level only; there is no Python REPL. "
                   "Install rlms (pip install rlms) and ensure Python 3.11+ for canonical RLM.",
        "plan_id": plan_id,
        "chunks_path": str(chunks_path),
        "chunk_count": len(chunks),
        "concurrency": cfg["concurrency"],
        "models": {
            "root": cfg["root_model"],
            "subagent": cfg["subagent_model"],
        },
        "orchestration_protocol": {
            "step_1": "Read chunks from `chunks_path`.",
            "step_2": (
                "Spawn up to `concurrency` Agent calls in parallel using `subagent_model`. "
                "Each agent receives one chunk + the original prompt; returns a structured extraction."
            ),
            "step_3": (
                "Collect all sub-agent outputs. Synthesize a final answer using `root_model` "
                "(or the current host model if it matches)."
            ),
            "step_4": "Return the final answer + a summary of which chunks contributed.",
        },
        "prompt": args.prompt,
    }

    print(json.dumps(instructions, indent=2))


if __name__ == "__main__":
    main()
