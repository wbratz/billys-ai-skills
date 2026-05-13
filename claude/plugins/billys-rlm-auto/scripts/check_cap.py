#!/usr/bin/env python3
"""
check_cap.py - deterministic cap-check for the rlm-auto skill.

Given a plan JSON (the JSON block emitted by rlm_plan.py), compares
`est_cost_usd.high` to the configured `auto_approve_cap_usd` and prints
a one-line verdict. The skill calls this script and trusts the exit
code so the cap is not honor-system at the comparison step.

Exit codes:
  0 - auto-approve
  1 - ask the user
  2 - input error (treated as ask, with reason logged)

Usage:
  py -3 check_cap.py --plan-json '<json>'
  py -3 check_cap.py --plan-file path/to/plan.json
  cat plan.json | py -3 check_cap.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULTS_PATH = Path(__file__).parent.parent / "config" / "defaults.json"
USER_CFG_PATH = Path(os.path.expanduser("~")) / ".rlm" / "auto-config.json"


def load_cap() -> float:
    cap = 0.50
    if DEFAULTS_PATH.is_file():
        try:
            cap = float(json.loads(DEFAULTS_PATH.read_text()).get("auto_approve_cap_usd", cap))
        except Exception:
            pass
    if USER_CFG_PATH.is_file():
        try:
            user = json.loads(USER_CFG_PATH.read_text())
            if "auto_approve_cap_usd" in user:
                cap = float(user["auto_approve_cap_usd"])
        except Exception:
            pass
    return cap


def _read_plan(args: argparse.Namespace) -> dict | None:
    if args.plan_json:
        return json.loads(args.plan_json)
    if args.plan_file:
        text = Path(args.plan_file).read_text(encoding="utf-8-sig", errors="replace")
        # rlm_plan.py emits a fenced JSON block at the end
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0]
        return json.loads(text)
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0]
    return json.loads(raw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-json", default=None, help="JSON string of the plan")
    ap.add_argument("--plan-file", default=None, help="Path to a file containing the plan")
    args = ap.parse_args()

    try:
        plan = _read_plan(args)
    except Exception as exc:
        print(f"decision=ask reason=plan_parse_error:{exc}")
        return 2

    if plan is None:
        print("decision=ask reason=no_plan_provided")
        return 2

    est = plan.get("est_cost_usd") or {}
    high = est.get("high")
    low = est.get("low")
    if not isinstance(high, (int, float)):
        print("decision=ask reason=missing_est_cost_high")
        return 2

    cap = load_cap()
    if high <= cap:
        print(f"decision=auto_approve cost_high={high:.2f} cap={cap:.2f}")
        return 0
    print(f"decision=ask cost_high={high:.2f} cap={cap:.2f} reason=cost_exceeds_cap")
    return 1


if __name__ == "__main__":
    sys.exit(main())
