# Modes

Three named profiles for budget/safety caps. Pick at plan time or let the planner auto-recommend.

## Mode table

| Mode | depth | iterations | timeout | errors | concurrency | Default env |
|---|---|---|---|---|---|---|
| **min** | 1 | 6 | 120s | 2 | 4 | ipython subprocess |
| **default** | 2 | 12 | 300s | 4 | 8 | ipython subprocess |
| **max** | 3 | 20 | 900s | 6 | 12 | ipython subprocess |

## When each is right

**min** - single doc Q&A, single short log, simple extraction. No recursion; just root + parallel `llm_query` fanout. Cheapest. Fastest to fail-or-finish.

**default** - the doc's recommended baseline. Corpus QA, directory analysis, most PDF synthesis, multi-doc research with moderate fanout. This is what 80% of real runs should use.

**max** - deep hierarchical synthesis where the structure of the task is genuinely tree-like. Monorepo audits, multi-PDF research where each PDF itself needs decomposition, exhaustive cross-corpus comparisons. Requires explicit `--max-budget=$X` to run as a guardrail.

## Why these specific values

### Depth

Going deeper than 2 multiplies cost by the fanout factor at each level - if root fires 8 subcalls and each fires 8, depth 3 = 64 sub-RLMs. The RLM paper itself flags recursion as worth it "only when the subtask itself needs multi-step reasoning." Most subtasks (extract, classify, summarize) want `llm_query` to Haiku, not `rlm_query`. So depth 2 is the right ceiling for typical work; depth 3 is reserved for genuinely hierarchical tasks.

### Iterations

12 is enough for: inspect context → plan → batch extract → gather → synthesize → refine → final. If the controller hasn't converged in 12, it's usually stuck in a loop rather than making slow progress. Going higher (20 in `max`) gives room for self-correction on truly hard synthesis, but the rlms compaction caveat (compaction only works in `local` env in upstream) means iteration count > ~20 in IPython subprocess will start bloating message history.

### Timeout

300s is 5 minutes - enough for most fanouts to complete at 8-wide Haiku concurrency. The timeout is checked between iterations, so the IPython subprocess `cell_timeout=30s` and `subcall_timeout` give inner-loop protection. Max mode allows 900s (15 min) for genuinely large hierarchical runs.

### Concurrency

This is the **breadth lever** - the doc's #1 community improvement. Fanout latency scales as `chunks / concurrency`:

- 50 chunks at 4-wide = 13 rounds (~3 min if each round is ~12s)
- 50 chunks at 8-wide = 7 rounds (~1.5 min)
- 50 chunks at 12-wide = 5 rounds (~1 min)

Min stays at 4 because tiny tasks don't have wide fanout anyway. Default at 8 hits the sweet spot for tier-2+ API limits. Max at 12 is the upper bound where we're confident in rlms thread-safety; higher requires explicit `--max-concurrent-subcalls=N` opt-in.

## Overrides

In the plan step, users can edit any field:

```
mode=default iterations=18 concurrency=10
mode=max --max-budget=10 root=claude-opus-4-7
```

The planner re-prints the plan with overrides applied and re-asks for approval.

## Hard requirements per mode

- **min**: no extra requirements.
- **default**: no extra requirements.
- **max**: requires `--max-budget=$N` (dollar cap). Runner aborts if the projected cost from the planner exceeds the budget.
