#!/usr/bin/env python3
"""
post_tool_use.py - PostToolUse + Stop hook.

Two modes:

1. Default (PostToolUse): given a tool-call payload, tally cumulative
   "bytes read directly", count read-tool calls, count rlm-script invocations,
   and stash a running tally in ~/.rlm/.session-<id>.json. Never blocks.

2. With --on-stop: on session end, fold the session tally into the most
   recent pending decision row as its `outcome`, then run the evaluator
   to attach a `grade`. Both are local-only writes.

Hook contract (Claude Code):
  - stdin: JSON describing the tool call (PostToolUse) or session
    (Stop / SubagentStop).
  - exit 0 -> non-blocking pass-through.

To wire as both PostToolUse and Stop, set two hook entries pointing at this
script, the Stop entry passing `--on-stop`.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from decision_log import attach_outcome, attach_grade, find_latest_pending, log_path  # noqa: E402
from evaluate import grade_row  # noqa: E402

SESSION_DIR = Path(os.path.expanduser("~")) / ".rlm"
SESSION_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:64]
    return SESSION_DIR / f".session-{safe or 'unknown'}.json"


def _load_session(session_id: str) -> dict:
    p = _session_path(session_id)
    if p.is_file():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {
        "ran": "direct",
        "tool_calls": 0,
        "read_tool_calls": 0,
        "bytes_read_directly": 0,
        "rlm_fanout": 0,
        "actual_cost_est_usd": 0.0,
        "wallclock_s": 0,
    }


def _save_session(session_id: str, data: dict) -> None:
    _session_path(session_id).write_text(json.dumps(data))


def _byte_size_of_read(payload: dict) -> int:
    """For Read tool calls, stat the target if we can."""
    args = payload.get("tool_input") or payload.get("toolInput") or {}
    path = args.get("file_path") or args.get("filePath") or args.get("path")
    if not path:
        return 0
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def handle_tool_use(payload: dict) -> int:
    session_id = (payload.get("session_id") or payload.get("sessionId")
                  or os.environ.get("CLAUDE_SESSION_ID") or "unknown")
    tool = (payload.get("tool_name") or payload.get("toolName") or "").lower()
    if not tool:
        return 0

    s = _load_session(session_id)
    s["tool_calls"] = int(s.get("tool_calls", 0)) + 1

    if tool == "read":
        s["read_tool_calls"] = int(s.get("read_tool_calls", 0)) + 1
        s["bytes_read_directly"] = int(s.get("bytes_read_directly", 0)) + _byte_size_of_read(payload)
    elif tool in ("grep", "glob"):
        s["read_tool_calls"] = int(s.get("read_tool_calls", 0)) + 1
    elif tool == "webfetch":
        s["read_tool_calls"] = int(s.get("read_tool_calls", 0)) + 1
        # WebFetch payload size is not surfaced in the hook input; we use a
        # fixed proxy (30 KB) so a fetched page contributes a non-zero amount
        # to bytes_read_directly. This underestimates large pages and
        # overestimates tiny ones - the grader's reason field documents this.
        s["bytes_read_directly"] = int(s.get("bytes_read_directly", 0)) + 30_000
    elif tool == "bash":
        # Look for rlm script invocations
        cmd = (payload.get("tool_input") or {}).get("command", "")
        if "rlm_run.py" in cmd or "rlm_native.py" in cmd:
            s["ran"] = "rlm"
        if "rlm_plan.py" in cmd:
            s.setdefault("planned", True)

    _save_session(session_id, s)
    return 0


def handle_stop(payload: dict) -> int:
    session_id = (payload.get("session_id") or payload.get("sessionId")
                  or os.environ.get("CLAUDE_SESSION_ID") or "unknown")
    s = _load_session(session_id)

    pending = find_latest_pending()
    if not pending:
        return 0

    outcome = {
        "ran": s.get("ran", "direct"),
        "tool_calls": s.get("tool_calls", 0),
        "read_tool_calls": s.get("read_tool_calls", 0),
        "bytes_read_directly": s.get("bytes_read_directly", 0),
        "rlm_fanout": s.get("rlm_fanout", 0),
        "actual_cost_est_usd": s.get("actual_cost_est_usd", 0.0),
        "wallclock_s": s.get("wallclock_s", 0),
    }
    attach_outcome(pending["decision_id"], outcome)

    # Grade right away
    pending["outcome"] = outcome
    grade = grade_row(pending)
    attach_grade(pending["decision_id"], grade)

    # Clean up session tally
    try:
        _session_path(session_id).unlink()
    except OSError:
        pass
    return 0


def _read_stdin_bytes() -> str:
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
        return 0

    if "--on-stop" in sys.argv:
        return handle_stop(payload)
    return handle_tool_use(payload)


if __name__ == "__main__":
    sys.exit(main())
