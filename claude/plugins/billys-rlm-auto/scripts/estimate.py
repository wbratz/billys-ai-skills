#!/usr/bin/env python3
"""
estimate.py - cost / speed / accuracy projection for the routing decision.

Given a classification result (from classify.py) and optionally the JSON plan
produced by rlm_plan.py, returns a small dict shaped like the "estimate" field
of a decision-log entry:

    {
      "rlm_cost_low": float, "rlm_cost_high": float,
      "direct_cost_low": float, "direct_cost_high": float,
      "savings_pct": int,
      "rlm_wallclock_s_est": int,
      "direct_wallclock_s_est": int,
      "accuracy_uplift_pp": float,
      "source": "paper:..." | "local-history" | "blended"
    }

Cost numbers in this module are projections from:
- Published Anthropic rates (Opus, Sonnet, Haiku) at the time of writing.
- BrowseComp-Plus headline cost numbers from the RLM paper (Zhang et al. 2026).

Once `~/.rlm/decisions.jsonl` has >=20 RLM rows, the median measured cost
overrides the projection (`source: "local-history"`).
"""

from __future__ import annotations

import json
import os
import statistics
from pathlib import Path

# Direct-call cost model: input is roughly bytes/4 tokens, output is small.
# We assume Opus 4.7 for direct since that's the model the user is on when
# this plugin runs.
OPUS_INPUT_PER_MTOK = 15.0
OPUS_OUTPUT_PER_MTOK = 75.0
HAIKU_INPUT_PER_MTOK = 0.80
HAIKU_OUTPUT_PER_MTOK = 4.0

# Paper-derived accuracy uplift on long-context tasks (avg across OOLONG,
# OOLONG-Pairs, BrowseComp-Plus, CodeQA). Conservative midpoint.
PAPER_ACCURACY_UPLIFT_PP = 28.3

LOG_PATH = Path(os.path.expanduser("~")) / ".rlm" / "decisions.jsonl"


def _direct_cost(size_bytes: int) -> tuple[float, float]:
    """Estimate cost if we just stuffed the input into Opus."""
    if size_bytes <= 0:
        # No path detected; assume modest direct cost (single-shot answer)
        return 0.05, 0.20
    in_tokens = size_bytes / 4
    out_tokens = 2500  # one-shot synthesis
    low = (in_tokens * OPUS_INPUT_PER_MTOK + out_tokens * OPUS_OUTPUT_PER_MTOK) / 1_000_000
    # Direct often pays for a retry or a refusal pass on long inputs; pad high.
    high = low * 1.8
    return round(low, 2), round(high, 2)


def _rlm_cost_from_plan(plan: dict | None, size_bytes: int) -> tuple[float, float]:
    """Pull the planner's cost range if provided; else compute from size."""
    if plan and isinstance(plan.get("est_cost_usd"), dict):
        lo = float(plan["est_cost_usd"].get("low", 0.0))
        hi = float(plan["est_cost_usd"].get("high", 0.0))
        if hi > 0:
            return round(lo, 2), round(hi, 2)
    # Fallback model: RLM uses cheap Haiku for fanout, Opus only on root.
    if size_bytes <= 0:
        return 0.05, 0.20
    haiku_tokens = (size_bytes / 4) * 0.7  # ~70% of input goes through Haiku
    opus_tokens = (size_bytes / 4) * 0.05  # ~5% summarized into Opus root
    out_tokens = 2500
    low = (haiku_tokens * HAIKU_INPUT_PER_MTOK
           + opus_tokens * OPUS_INPUT_PER_MTOK
           + out_tokens * OPUS_OUTPUT_PER_MTOK) / 1_000_000
    high = low * 2.5  # RLM has high variance
    return round(low, 2), round(high, 2)


def _local_history() -> dict | None:
    """Median measured RLM cost from the local decision log, if any."""
    if not LOG_PATH.is_file():
        return None
    rlm_costs = []
    for line in LOG_PATH.read_text(errors="replace").splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("outcome", {}).get("ran") == "rlm":
            c = row.get("outcome", {}).get("actual_cost_est_usd")
            if isinstance(c, (int, float)) and c > 0:
                rlm_costs.append(float(c))
    if len(rlm_costs) < 20:
        return None
    return {
        "median": statistics.median(rlm_costs),
        "p25": statistics.quantiles(rlm_costs, n=4)[0],
        "p75": statistics.quantiles(rlm_costs, n=4)[2],
        "n": len(rlm_costs),
    }


def estimate(classification: dict, plan: dict | None = None) -> dict:
    size_bytes = int(classification.get("totals", {}).get("size_bytes", 0))
    file_count = int(classification.get("totals", {}).get("file_count", 0))

    rlm_low, rlm_high = _rlm_cost_from_plan(plan, size_bytes)
    direct_low, direct_high = _direct_cost(size_bytes)

    source = "paper:browsecomp-plus"
    hist = _local_history()
    if hist:
        # Blend: pin RLM cost to the local median, keep range from p25/p75
        rlm_low = round(hist["p25"], 2)
        rlm_high = round(hist["p75"], 2)
        source = f"local-history(n={hist['n']})"
    elif plan:
        source = "planner+paper"

    # Savings: midpoint comparison
    rlm_mid = (rlm_low + rlm_high) / 2
    direct_mid = (direct_low + direct_high) / 2
    if direct_mid > 0:
        savings_pct = int(round((1 - rlm_mid / direct_mid) * 100))
    else:
        savings_pct = 0

    # Wallclock: rough projection. Direct is one Opus call (~30-60s) but
    # may need multiple read passes. RLM fans out cheap subcalls.
    direct_wall = max(20, int(size_bytes / 20_000))  # ~1s per 20KB read
    rlm_wall = max(30, int(size_bytes / 80_000))     # parallel Haiku fanout

    # Accuracy uplift only meaningful at scale
    if size_bytes >= 100_000 or file_count >= 10:
        acc = PAPER_ACCURACY_UPLIFT_PP
    elif size_bytes >= 51_200:
        acc = PAPER_ACCURACY_UPLIFT_PP / 2
    else:
        acc = 0.0

    return {
        "rlm_cost_low": rlm_low,
        "rlm_cost_high": rlm_high,
        "direct_cost_low": direct_low,
        "direct_cost_high": direct_high,
        "savings_pct": max(-100, min(100, savings_pct)),
        "rlm_wallclock_s_est": rlm_wall,
        "direct_wallclock_s_est": direct_wall,
        "accuracy_uplift_pp": round(acc, 1),
        "source": source,
    }


def render_footer(est: dict, mode: str = "RLM", log_path: str = str(LOG_PATH)) -> str:
    return (
        f"[rlm-auto] used {mode} "
        f"(est ${est['rlm_cost_low']:.2f}-${est['rlm_cost_high']:.2f}, "
        f"~{est['savings_pct']}% vs direct, "
        f"+{est['accuracy_uplift_pp']}pp acc projected, "
        f"log: {log_path})"
    )


def main() -> None:
    import argparse
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--classification", help="Path to classify.py JSON output, or '-' for stdin")
    ap.add_argument("--plan", help="Path to rlm_plan.py JSON output (optional)")
    args = ap.parse_args()

    def _read_robust(p: Path) -> str:
        raw = p.read_bytes()
        for enc in ("utf-8-sig", "utf-16", "utf-8", "cp1252"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")

    if args.classification == "-" or args.classification is None:
        cls = json.loads(sys.stdin.read())
    else:
        cls = json.loads(_read_robust(Path(args.classification)))

    plan = None
    if args.plan:
        text = _read_robust(Path(args.plan))
        # rlm_plan emits a fenced JSON block at the end; pull it out
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0]
        plan = json.loads(text)

    est = estimate(cls, plan=plan)
    print(json.dumps(est, indent=2))


if __name__ == "__main__":
    main()
