#!/usr/bin/env python3
"""
evaluate.py - local-only post-hoc grader for routing decisions.

For each row in the decision log that has an outcome but no grade, this
script applies a small set of heuristics and writes a `grade` field:

    grade = {
      "verdict_grade": "correct" | "false_positive" | "false_negative" |
                       "unclear" | "indeterminate",
      "reason": str,
      "false_positive": bool,   # decided RLM but should have gone direct
      "false_negative": bool,   # decided direct but should have used RLM
      "needs_review": bool      # heuristic isn't confident; flag for human
    }

Grading rules (heuristic, NOT ground truth - that's the whole point of
the `needs_review` flag):

  verdict=rlm, outcome.ran=rlm:
    - If actual_cost < $0.05 AND no fanout happened -> false_positive
      (overkill: input was tiny in practice).
    - Else -> correct (we caught the right class of task).

  verdict=direct, outcome.ran=direct:
    - If bytes_read_directly > min_size_bytes
      OR tool_calls reading content > 10
      -> false_negative (Claude blew context anyway, RLM would have helped).
    - Else -> correct.

  verdict=ambiguous, outcome.ran=rlm:
    - Same as verdict=rlm above; we leaned in and graded the lean.

  Anything with outcome=None -> indeterminate (the task never finished
  cleanly or the Stop hook didn't fire).

The grader is intentionally simple and CONSERVATIVE about marking errors.
Marginal cases all go to "unclear" with needs_review=true, so the human
review queue surfaces them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from decision_log import read_all, attach_grade, user_cfg, log_path


def _cfg_thresholds() -> dict:
    cfg = user_cfg()
    return {
        "min_size_bytes": cfg.get("min_size_bytes", 51200),
        "min_file_count": cfg.get("min_file_count", 5),
        "max_direct_read_calls": cfg.get("max_direct_read_calls", 10),
        "fp_tiny_cost_threshold": cfg.get("fp_tiny_cost_threshold", 0.05),
    }


def grade_row(row: dict) -> dict:
    th = _cfg_thresholds()
    outcome = row.get("outcome") or {}
    verdict = row.get("verdict", "direct")
    totals = row.get("totals", {})

    if not outcome:
        return {
            "verdict_grade": "indeterminate",
            "reason": "no outcome recorded (session ended without Stop hook, or task aborted)",
            "false_positive": False,
            "false_negative": False,
            "needs_review": False,
        }

    ran = outcome.get("ran")
    bytes_read_direct = int(outcome.get("bytes_read_directly", 0))
    tool_calls_read = int(outcome.get("read_tool_calls", outcome.get("tool_calls", 0)))
    actual_cost = float(outcome.get("actual_cost_est_usd", 0.0))
    fanout = int(outcome.get("rlm_fanout", 0))

    # Case 1: routed to RLM
    if verdict in ("rlm", "ambiguous") and ran == "rlm":
        if actual_cost < th["fp_tiny_cost_threshold"] and fanout == 0:
            return {
                "verdict_grade": "false_positive",
                "reason": f"RLM ran but cost ${actual_cost:.2f} with no fanout - input fit one prompt; overkill",
                "false_positive": True,
                "false_negative": False,
                "needs_review": False,
            }
        return {
            "verdict_grade": "correct",
            "reason": f"RLM ran on {totals.get('size_bytes', 0)//1024} KB / {totals.get('file_count', 0)} files; fanout={fanout}",
            "false_positive": False,
            "false_negative": False,
            "needs_review": False,
        }

    # Case 2: routed direct, ran direct
    if verdict == "direct" and ran == "direct":
        if (bytes_read_direct >= th["min_size_bytes"]
                or tool_calls_read > th["max_direct_read_calls"]):
            return {
                "verdict_grade": "false_negative",
                "reason": (f"direct path read {bytes_read_direct//1024} KB via "
                           f"{tool_calls_read} tool calls; exceeded RLM thresholds"),
                "false_positive": False,
                "false_negative": True,
                "needs_review": False,
            }
        return {
            "verdict_grade": "correct",
            "reason": f"direct path read {bytes_read_direct//1024} KB; well under threshold",
            "false_positive": False,
            "false_negative": False,
            "needs_review": False,
        }

    # Case 3: routed ambiguous, ran direct
    if verdict == "ambiguous" and ran == "direct":
        if bytes_read_direct >= th["min_size_bytes"]:
            return {
                "verdict_grade": "false_negative",
                "reason": "ambiguous -> direct, but direct path read >= threshold; should have leaned RLM",
                "false_positive": False,
                "false_negative": True,
                "needs_review": True,
            }
        return {
            "verdict_grade": "unclear",
            "reason": "ambiguous routing; direct path stayed under threshold but borderline",
            "false_positive": False,
            "false_negative": False,
            "needs_review": True,
        }

    # Case 4: anything else (verdict and ran don't match expected combos)
    return {
        "verdict_grade": "unclear",
        "reason": f"verdict={verdict} ran={ran} - unexpected combination; review manually",
        "false_positive": False,
        "false_negative": False,
        "needs_review": True,
    }


def grade_all() -> dict:
    """Grade every row that has an outcome but no grade. Returns summary."""
    rows = read_all()
    summary = {
        "total": len(rows),
        "graded_this_run": 0,
        "correct": 0,
        "false_positive": 0,
        "false_negative": 0,
        "unclear": 0,
        "indeterminate": 0,
        "needs_review": 0,
        "savings_realized_usd": 0.0,
        "spent_on_rlm_usd": 0.0,
    }
    for row in rows:
        if row.get("grade"):
            g = row["grade"]
        elif row.get("outcome"):
            g = grade_row(row)
            attach_grade(row["decision_id"], g)
            summary["graded_this_run"] += 1
        else:
            continue
        gv = g.get("verdict_grade", "indeterminate")
        summary[gv] = summary.get(gv, 0) + 1
        if g.get("needs_review"):
            summary["needs_review"] += 1
        # Tally money
        out = row.get("outcome") or {}
        est = row.get("estimate") or {}
        if out.get("ran") == "rlm":
            summary["spent_on_rlm_usd"] += float(out.get("actual_cost_est_usd", 0.0))
            direct_mid = (est.get("direct_cost_low", 0) + est.get("direct_cost_high", 0)) / 2
            actual = float(out.get("actual_cost_est_usd", 0.0))
            summary["savings_realized_usd"] += max(0.0, direct_mid - actual)
    summary["spent_on_rlm_usd"] = round(summary["spent_on_rlm_usd"], 2)
    summary["savings_realized_usd"] = round(summary["savings_realized_usd"], 2)
    return summary


def review_queue() -> list[dict]:
    """Rows the grader couldn't be confident about - dogfood candidates."""
    return [r for r in read_all() if r.get("grade", {}).get("needs_review")]


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("grade-all")
    sub.add_parser("review-queue")
    sub.add_parser("summary")
    args = ap.parse_args()

    if args.cmd == "grade-all":
        print(json.dumps(grade_all(), indent=2))
    elif args.cmd == "review-queue":
        print(json.dumps(review_queue(), indent=2))
    elif args.cmd == "summary":
        # Implicitly grade pending, then print summary
        print(json.dumps(grade_all(), indent=2))


if __name__ == "__main__":
    main()
