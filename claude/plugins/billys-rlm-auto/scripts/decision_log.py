#!/usr/bin/env python3
"""
decision_log.py - append-only JSONL writer/reader for rlm-auto decisions.

Lives at ~/.rlm/decisions.jsonl by default. Never leaves the machine.
Stdlib-only. Atomic appends via O_APPEND.

Schema (each row):

    {
      "ts": ISO8601,
      "session_id": str,        # Claude Code session id if available
      "decision_id": str,       # UUID per decision
      "prompt_hash": str,       # SHA-256[:16] of the prompt
      "prompt_len": int,
      "prompt_full": str|null,  # only if log_full_prompts=true
      "signals": [...],         # from classify.py
      "verdict": "rlm"|"direct"|"ambiguous",
      "auto_approved": bool,    # rlm-auto skipped the approval gate
      "estimate": {...},        # from estimate.py
      "outcome": {...} | null,  # filled by PostToolUse / Stop hook
      "grade": {...} | null     # filled by evaluator
    }
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import uuid
from pathlib import Path

DEFAULT_LOG = Path(os.path.expanduser("~")) / ".rlm" / "decisions.jsonl"


def log_path() -> Path:
    """Honor user config override; create parent dir."""
    user_cfg_path = Path(os.path.expanduser("~")) / ".rlm" / "auto-config.json"
    path = DEFAULT_LOG
    if user_cfg_path.is_file():
        try:
            cfg = json.loads(user_cfg_path.read_text())
            override = cfg.get("log_path")
            if override:
                path = Path(os.path.expanduser(override))
        except Exception:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# Backwards-compat alias for any external caller importing _log_path.
_log_path = log_path


def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def user_cfg() -> dict:
    p = Path(os.path.expanduser("~")) / ".rlm" / "auto-config.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


_user_cfg = user_cfg


def write_decision(
    prompt: str,
    classification: dict,
    estimate_data: dict,
    verdict: str,
    auto_approved: bool,
    session_id: str | None = None,
) -> str:
    """Append a new decision row. Returns the decision_id."""
    cfg = user_cfg()
    decision_id = uuid.uuid4().hex[:12]
    row = {
        "ts": _now_iso(),
        "session_id": session_id or os.environ.get("CLAUDE_SESSION_ID") or "unknown",
        "decision_id": decision_id,
        "prompt_hash": _hash_prompt(prompt),
        "prompt_len": len(prompt),
        "prompt_full": prompt if cfg.get("log_full_prompts") else None,
        "signals": classification.get("signals", []),
        "totals": classification.get("totals", {}),
        "score": classification.get("score"),
        "verdict": verdict,
        "auto_approved": auto_approved,
        "estimate": estimate_data,
        "outcome": None,
        "grade": None,
    }
    path = log_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return decision_id


def attach_outcome(decision_id: str, outcome: dict) -> bool:
    """Update an existing row's outcome. Rewrites the file once."""
    return _patch_row(decision_id, "outcome", outcome)


def attach_grade(decision_id: str, grade: dict) -> bool:
    return _patch_row(decision_id, "grade", grade)


def _patch_row(decision_id: str, field: str, value: dict) -> bool:
    # NOTE: O(N) full-file rewrite on every patch. Fine at hundreds of rows;
    # revisit if the log routinely exceeds tens of thousands of entries.
    path = log_path()
    if not path.is_file():
        return False
    rows = []
    found = False
    for line in path.read_text(errors="replace").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("decision_id") == decision_id:
            r[field] = value
            found = True
        rows.append(r)
    if not found:
        return False
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    tmp.replace(path)
    return True


def read_all() -> list[dict]:
    path = log_path()
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def find_latest_pending() -> dict | None:
    """Find the most recent row that has no outcome attached yet."""
    rows = read_all()
    for r in reversed(rows):
        if r.get("outcome") is None:
            return r
    return None


def main() -> None:
    """CLI: subcommands write, attach-outcome, attach-grade, dump."""
    import argparse
    import sys

    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_dump = sub.add_parser("dump")
    p_dump.add_argument("--limit", type=int, default=None)

    p_path = sub.add_parser("path")

    p_attach = sub.add_parser("attach-outcome")
    p_attach.add_argument("--decision-id", required=True)
    p_attach.add_argument("--outcome-json", required=True,
                          help="JSON string OR '-' to read from stdin")

    p_grade = sub.add_parser("attach-grade")
    p_grade.add_argument("--decision-id", required=True)
    p_grade.add_argument("--grade-json", required=True)

    args = ap.parse_args()

    if args.cmd == "dump":
        rows = read_all()
        if args.limit:
            rows = rows[-args.limit:]
        for r in rows:
            print(json.dumps(r))
    elif args.cmd == "path":
        print(_log_path())
    elif args.cmd == "attach-outcome":
        data = sys.stdin.read() if args.outcome_json == "-" else args.outcome_json
        ok = attach_outcome(args.decision_id, json.loads(data))
        print(json.dumps({"ok": ok}))
    elif args.cmd == "attach-grade":
        data = sys.stdin.read() if args.grade_json == "-" else args.grade_json
        ok = attach_grade(args.decision_id, json.loads(data))
        print(json.dumps({"ok": ok}))


if __name__ == "__main__":
    main()
