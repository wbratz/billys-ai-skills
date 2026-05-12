#!/usr/bin/env python3
"""
rlm_run.py — canonical RLM runner (wraps the upstream `rlms` package).

Loads context via the loaders/, configures an RLM with mode-appropriate models,
runs it under IPython subprocess by default, and emits a JSON result.

Usage:
  python rlm_run.py --target <path|url> --prompt "<question>" --mode <min|default|max>
                    [--max-budget N] [--environment ipython|local]
                    [--log-dir .rlm/logs] [--override-model root=X depth1=Y ...]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

MODE_CONFIGS = {
    "min": {
        "max_depth": 1, "max_iterations": 6, "max_timeout": 120,
        "max_errors": 2, "max_concurrent_subcalls": 4,
        "root_model": "claude-sonnet-4-6",
        "depth1_model": None,
        "depth2_model": None,
        "llm_query_model": "claude-haiku-4-5-20251001",
    },
    "default": {
        "max_depth": 2, "max_iterations": 12, "max_timeout": 300,
        "max_errors": 4, "max_concurrent_subcalls": 8,
        "root_model": "claude-opus-4-7",
        "depth1_model": "claude-sonnet-4-6",
        "depth2_model": None,
        "llm_query_model": "claude-haiku-4-5-20251001",
    },
    "max": {
        "max_depth": 3, "max_iterations": 20, "max_timeout": 900,
        "max_errors": 6, "max_concurrent_subcalls": 12,
        "root_model": "claude-opus-4-7",
        "depth1_model": "claude-sonnet-4-6",
        "depth2_model": "claude-haiku-4-5-20251001",
        "llm_query_model": "claude-haiku-4-5-20251001",
    },
}

SYSTEM_PROMPT_ADDENDUM = """
You are running inside an RLM loop. The full task context is in the REPL
variable `context` (and `context_0`, `context_1`, ...). Do not assume the
context fits in this prompt — inspect it from the REPL.

Rules:
- Use llm_query_batched for parallel chunk extraction (cheap, fast).
- Use rlm_query only for subtasks that genuinely need multi-step reasoning.
- At depth 2 (max mode only), pass model="claude-haiku-4-5-20251001" to rlm_query.
- Create a named result variable, then emit FINAL_VAR(name). Do not use bare FINAL.
- Print short diagnostics, never the whole context.
- If a subcall returns "Error:", inspect and recover.
"""


def fail(msg: str, code: int = 1) -> None:
    print(json.dumps({"ok": False, "error": msg}), file=sys.stderr)
    sys.exit(code)


def load_context(target: str, max_bytes: int | None) -> list[dict]:
    from loaders.load_file import load as load_file
    from loaders.load_dir import load as load_dir
    from loaders.load_pdf import load as load_pdf
    from loaders.load_url import load as load_url
    from loaders.load_logs import load as load_logs

    if target.startswith(("http://", "https://")):
        return load_url(target, max_bytes=max_bytes)
    p = Path(target)
    if not p.exists():
        fail(f"Target not found: {target}")
    if p.is_dir():
        return load_dir(p, max_bytes=max_bytes)
    suf = p.suffix.lower()
    if suf == ".pdf":
        return load_pdf(p, max_bytes=max_bytes)
    if suf in {".log", ".jsonl", ".ndjson"}:
        return load_logs(p, max_bytes=max_bytes)
    return load_file(p, max_bytes=max_bytes)


def parse_overrides(args: list[str]) -> dict:
    out = {}
    for a in args:
        if "=" not in a:
            continue
        k, v = a.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def main() -> None:
    if sys.version_info < (3, 11):
        fail(
            "RLM requires Python 3.11 or newer. "
            "Create a Python 3.11+ environment and reinstall: python -m pip install --upgrade rlms"
        )

    try:
        from rlm import RLM
        from rlm.logger import RLMLogger
    except Exception as exc:
        fail(
            f"Could not import the `rlms` package ({exc}). "
            "Install with: python -m pip install --upgrade rlms"
        )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        fail("ANTHROPIC_API_KEY is not set. Export it in your shell before running.")

    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--mode", default="default", choices=["min", "default", "max"])
    parser.add_argument("--max-budget", type=float, default=None,
                        help="Required for mode=max. USD cap.")
    parser.add_argument("--max-bytes", type=int, default=None)
    parser.add_argument("--environment", default="ipython", choices=["ipython", "local"])
    parser.add_argument("--log-dir", default=".rlm/logs")
    parser.add_argument("--plan-id", default=None)
    parser.add_argument("override", nargs="*",
                        help="Per-call overrides: root=<model> depth1=<model> llm_query=<model>")
    args = parser.parse_args()

    if args.mode == "max" and args.max_budget is None:
        fail("mode=max requires --max-budget=$N (USD cap).")

    cfg = dict(MODE_CONFIGS[args.mode])
    overrides = parse_overrides(args.override)
    if "root" in overrides:
        cfg["root_model"] = overrides["root"]
    if "depth1" in overrides:
        cfg["depth1_model"] = overrides["depth1"] if overrides["depth1"] != "none" else None
    if "depth2" in overrides:
        cfg["depth2_model"] = overrides["depth2"] if overrides["depth2"] != "none" else None
    if "llm_query" in overrides:
        cfg["llm_query_model"] = overrides["llm_query"]
    if "iterations" in overrides:
        cfg["max_iterations"] = int(overrides["iterations"])
    if "timeout" in overrides:
        cfg["max_timeout"] = int(overrides["timeout"])
    if "concurrency" in overrides:
        cfg["max_concurrent_subcalls"] = int(overrides["concurrency"])

    context = load_context(args.target, args.max_bytes)
    if not context:
        fail("No content loaded from target.")

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    plan_id = args.plan_id or uuid.uuid4().hex[:8]
    log_path = log_dir / f"rlm-{plan_id}.jsonl"

    logger = RLMLogger(log_dir=str(log_dir), log_file_name=log_path.name)

    env_kwargs = {}
    if args.environment == "ipython":
        env_kwargs = {
            "kernel_mode": "subprocess",
            "cell_timeout": 30,
            "startup_timeout": 60,
            "subcall_timeout": cfg["max_timeout"],
        }

    rlm_kwargs = dict(
        backend="anthropic",
        backend_kwargs={"model_name": cfg["root_model"]},
        environment=args.environment,
        environment_kwargs=env_kwargs,
        max_depth=cfg["max_depth"],
        max_iterations=cfg["max_iterations"],
        max_timeout=cfg["max_timeout"],
        max_errors=cfg["max_errors"],
        max_concurrent_subcalls=cfg["max_concurrent_subcalls"],
        compaction=False,
        logger=logger,
        system_prompt_addendum=SYSTEM_PROMPT_ADDENDUM,
        default_subcall_model=cfg["llm_query_model"],
    )
    if cfg["depth1_model"]:
        rlm_kwargs["other_backend"] = "anthropic"
        rlm_kwargs["other_backend_kwargs"] = {"model_name": cfg["depth1_model"]}

    if args.max_budget is not None:
        rlm_kwargs["max_budget"] = args.max_budget

    rlm = RLM(**rlm_kwargs)

    try:
        result = rlm.completion(context, root_prompt=args.prompt)
    except Exception as exc:
        fail(f"RLM run failed: {exc}")
    finally:
        try:
            rlm.close()
        except Exception:
            pass

    answer = getattr(result, "response", None) or str(result)
    exec_time = getattr(result, "execution_time", None)
    usage = getattr(result, "usage_summary", None)
    usage_dict = usage.to_dict() if usage and hasattr(usage, "to_dict") else {}

    print(json.dumps({
        "ok": True,
        "plan_id": plan_id,
        "mode": args.mode,
        "answer": answer,
        "execution_time": exec_time,
        "usage_summary": usage_dict,
        "trajectory_log": str(log_path),
    }, default=str, indent=2))


if __name__ == "__main__":
    main()
