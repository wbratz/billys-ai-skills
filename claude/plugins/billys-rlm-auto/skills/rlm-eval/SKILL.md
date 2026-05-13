---
name: rlm-eval
description: Local-only evaluator for rlm-auto routing decisions. Invoke on /rlm-auto:status, when the user asks "how accurate is the router?", "show me the false positives", or wants the dogfood report. Reads ~/.rlm/decisions.jsonl, attaches grades to any ungraded rows, and prints a summary plus a review queue of cases the grader was not confident about. Never sends anything off the machine.
triggers:
  - "/rlm-auto:status"
  - "rlm-auto status"
  - "how accurate is the router"
  - "rlm decision log"
  - "rlm review queue"
  - "show me the false positives"
---

# rlm-eval skill

The evaluator turns the raw decision log into actionable feedback for tuning
the classifier. It is the dogfood loop.

## When to invoke

- The user runs `/rlm-auto:status`.
- The user asks how the router is performing, what it cost, or what it saved.
- The user wants to review borderline cases.
- After making a config change, to confirm the new thresholds behave as expected.

## How to run

### 1. Summary report

```bash
py -3 "${CLAUDE_PLUGIN_ROOT}/scripts/evaluate.py" summary
```

This grades any new rows, then prints a JSON summary. Render it for the user as:

```
rlm-auto status (log: ~/.rlm/decisions.jsonl)
  Decisions logged:        N
  Graded this run:         N
  Correct:                 N  (%)
  False positive (RLM):    N  (%)  - cases where RLM was overkill
  False negative (direct): N  (%)  - cases where we should have used RLM
  Unclear:                 N
  Indeterminate:           N        - no outcome attached
  Needs human review:      N

  Spent on RLM (cumulative):     $X.XX
  Realized savings vs direct:    $X.XX
```

### 2. Review queue

```bash
py -3 "${CLAUDE_PLUGIN_ROOT}/scripts/evaluate.py" review-queue
```

These are the rows where the grader's heuristic was not confident. Read out
each entry's `prompt_hash`, `signals`, `verdict`, and `grade.reason`. Offer
the user three actions per entry:

- **"verdict_correct"** -> no change needed; the heuristic just couldn't tell.
- **"verdict_wrong: should_have_used_rlm"** -> teaches the grader what a FN looks like.
- **"verdict_wrong: should_have_gone_direct"** -> teaches the grader what a FP looks like.

When the user gives a verdict, update that row's `grade` via
`decision_log.py attach-grade`, and propose a config edit through
`/rlm-auto:config` if a pattern emerges (e.g., "you've marked five
'corpus_noun + small_file' rows as direct - lower kw weight?").

### 3. Tuning recommendations

After the summary + review pass, look at the cumulative grades and offer
*specific*, narrow recommendations. Examples (only suggest if the data
supports them):

- ">3 false positives in a row at size <30KB" -> raise `min_size_bytes`.
- ">3 false negatives where bytes_read_directly > 200KB" -> add
  matching keywords or lower `min_size_bytes`.
- "ambiguous band keeps going direct and being wrong" -> shrink the band.

NEVER recommend changes that aren't supported by the log. If there's no
clear pattern, say so.

## Rules

- This skill is read-only on the decision log except via `evaluate.py`
  and the documented `decision_log.py` subcommands.
- Never print prompt content - only `prompt_hash` and `signals` - unless
  the user has set `log_full_prompts: true` AND explicitly asked.
- Honestly surface the grader's heuristic nature. If the user pushes back
  on a grade, accept their correction and update the row.
- The goal is dogfood feedback, not vanity metrics. If the data is too
  thin to draw conclusions, say "not enough decisions yet" rather than
  making things up.
