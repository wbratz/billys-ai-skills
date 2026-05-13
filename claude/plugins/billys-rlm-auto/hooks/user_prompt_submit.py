#!/usr/bin/env python3
"""
user_prompt_submit.py - UserPromptSubmit hook.

Reads the hook payload on stdin, classifies the prompt, writes a pending
decision row to the log, and emits a <system-reminder> on stdout that tells
Claude what to do.

The reminder is the only channel by which we influence Claude's behavior.
It contains:
  - The verdict (rlm / direct / ambiguous)
  - The signals that drove it (so Claude can sanity-check)
  - The cost/speed/accuracy estimate
  - The decision_id (so the answer can attach an outcome later)
  - Instructions on how to route

Hook contract (Claude Code):
  - stdin: JSON with { "prompt": str, "session_id": str, "cwd": str, ... }
  - exit 0 -> stdout is appended to the conversation as a system reminder
  - exit non-zero -> hook is reported as failed but doesn't block the prompt

This script NEVER blocks the prompt, NEVER calls an LLM, and NEVER reaches
the network. It is stdlib-only and bounded.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Hook file location: <plugin_root>/hooks/user_prompt_submit.py
# scripts/ is a sibling of hooks/
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from classify import classify, load_config  # noqa: E402
from estimate import estimate  # noqa: E402
from decision_log import write_decision  # noqa: E402


def _read_stdin_bytes() -> str:
    """Read stdin as bytes and decode robustly across BOMs and encodings."""
    try:
        buf = sys.stdin.buffer.read()
    except AttributeError:
        buf = sys.stdin.read().encode("utf-8", errors="replace")
    if not buf:
        return ""
    for enc in ("utf-8-sig", "utf-16", "utf-8", "cp1252"):
        try:
            return buf.decode(enc)
        except UnicodeDecodeError:
            continue
    return buf.decode("utf-8", errors="replace")


def main() -> int:
    raw = _read_stdin_bytes() or "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # Hook payload malformed; do nothing, don't block.
        return 0

    prompt = payload.get("prompt", "")
    if not prompt:
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    session_id = payload.get("session_id") or payload.get("sessionId")

    cfg = load_config()
    if not cfg.get("enabled", True):
        return 0

    cls = classify(prompt, cwd=cwd)
    if cls["verdict"] == "direct" and cls["score"] < 0.05:
        # Strong direct signal - don't even bother writing to log
        return 0

    est = estimate(cls, plan=None)
    decision_id = write_decision(
        prompt=prompt,
        classification=cls,
        estimate_data=est,
        verdict=cls["verdict"],
        auto_approved=False,
        session_id=session_id,
    )

    # Build the reminder
    cap = cfg.get("auto_approve_cap_usd", 0.50)
    signals_txt = "; ".join(s["detail"] for s in cls["signals"][:5]) or "(none)"

    if cls["verdict"] == "rlm":
        body = (
            f"rlm-auto: this task looks RLM-shaped (score={cls['score']}).\n"
            f"Signals: {signals_txt}\n"
            f"Estimate: RLM ~${est['rlm_cost_low']:.2f}-${est['rlm_cost_high']:.2f} "
            f"vs direct ~${est['direct_cost_low']:.2f}-${est['direct_cost_high']:.2f} "
            f"(savings ~{est['savings_pct']}%, +{est['accuracy_uplift_pp']}pp acc projected).\n"
            f"Decision: route via the rlm-auto skill. "
            f"If est_cost_high <= ${cap:.2f}, run RLM without asking the user. "
            f"Above the cap, ask once with a one-line cost prompt.\n"
            f"Decision ID: {decision_id}. After completion, the post_tool_use hook "
            f"will attach an outcome to this decision automatically; the rlm-auto "
            f"skill should append a footer like '[rlm-auto] used RLM (...)' to the "
            f"final answer."
        )
    elif cls["verdict"] == "ambiguous":
        body = (
            f"rlm-auto: this task is borderline (score={cls['score']}).\n"
            f"Signals: {signals_txt}\n"
            f"Estimate: RLM ~${est['rlm_cost_low']:.2f}-${est['rlm_cost_high']:.2f} "
            f"vs direct ~${est['direct_cost_low']:.2f}-${est['direct_cost_high']:.2f}.\n"
            f"Decision: if the user's question requires reasoning ACROSS the inputs "
            f"(not a single lookup), prefer RLM. Otherwise proceed direct. "
            f"No footer needed if going direct.\n"
            f"Decision ID: {decision_id}."
        )
    else:
        body = (
            f"rlm-auto: classified DIRECT (score={cls['score']}).\n"
            f"Signals: {signals_txt}\n"
            f"Decision: proceed normally. Decision ID: {decision_id} "
            f"(logged so the evaluator can grade the routing call later)."
        )

    print(f"<system-reminder>\n{body}\n</system-reminder>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
