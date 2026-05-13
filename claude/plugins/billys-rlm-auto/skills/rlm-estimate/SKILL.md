---
name: rlm-estimate
description: Renders a transparent cost/speed/accuracy estimate for an RLM vs. direct-execution decision. Invoke whenever a user asks "what did that cost?", "what would direct have cost?", "show me the estimate", or when the rlm-auto skill needs the footer numbers and the system reminder didn't carry them. Sources: published Anthropic rates, the RLM paper benchmarks, and once available the user's local decision history.
triggers:
  - "what did that cost"
  - "rlm estimate"
  - "estimate the savings"
  - "what would direct cost"
  - "/rlm-auto:estimate"
---

# rlm-estimate skill

A small skill that wraps `scripts/estimate.py` and formats its output for
humans. Used by `rlm-auto` to render the answer footer, and exposed to the
user so they can sanity-check the routing call after the fact.

## When to invoke

- `rlm-auto` needs estimate numbers but the system reminder didn't carry them.
- The user asks any of: "what did that cost?", "would direct have been cheaper?",
  "what's the projected savings?".
- After grading, when the user wants to see actual-vs-estimated for a decision.

## How to run

1. **Get the classification.** Either re-run `classify.py` on the prompt, or
   pull it from the decision log if you have the decision_id:

   ```bash
   py -3 "${CLAUDE_PLUGIN_ROOT}/scripts/decision_log.py" dump --limit 1
   ```

2. **Run the estimator.** Pipe the classification JSON into `estimate.py`.
   Optionally pass the planner output via `--plan` for tighter numbers:

   ```bash
   echo '<classification-json>' | py -3 \
     "${CLAUDE_PLUGIN_ROOT}/scripts/estimate.py" --classification -
   ```

3. **Render the result.** Use this format unless the user asks for raw JSON:

   ```
   rlm-auto estimate
     RLM         $L.LL - $H.HH   (~W seconds, ~Z% savings vs direct)
     Direct      $L.LL - $H.HH   (~W seconds)
     Accuracy    +Xpp projected (long-context tasks per RLM paper)
     Source      <paper:... | local-history(n=N) | planner+paper>
   ```

4. **Caveat clearly.** Add one line explaining that until the user has
   >=20 logged RLM decisions, "savings" is a published-benchmark
   projection, not a measurement.

## Rules

- Numbers come from the estimator, not your judgment. Do not adjust them.
- Show the `source` field verbatim so the user knows what backed the estimate.
- Never claim "we saved $X" unless `outcome.actual_cost_est_usd` is in
  the log row. Pre-outcome figures are "projected".
