# Model Routing

How Haiku, Sonnet, and Opus map to RLM call sites in this plugin.

## The principle

RLM has three classes of LLM calls, each with very different cost/capability profiles:

| Call type | Frequency per run | Reasoning required |
|---|---|---|
| **Root controller** (depth 0) | 1 conversation, ~6-20 turns | Highest - plans decomposition, writes Python, synthesizes |
| **Child RLM** (depth 1+) | 0-N parallel sub-loops | Moderate - multi-step reasoning over a sub-chunk |
| **`llm_query` one-shot** | 10s to 100s, parallel | Low - extract, classify, summarize one chunk |

Right model for each job:

- **Highest reasoning, lowest volume → Opus 4.7.** The root controller carries the whole task. A capable model here pays back many times over by making better decomposition decisions.
- **Moderate reasoning, moderate volume → Sonnet 4.6.** Child RLMs are doing real multi-step work but bounded to a sub-chunk. Sonnet's cost/quality is right.
- **Cheap classification at scale → Haiku 4.5.** This is where breadth lives. Fast, cheap, parallel-friendly.

## Per-mode routing table

| Mode | Root (depth 0) | Depth 1 (`other_backend_client`) | Depth 2 (explicit `model=`) | `llm_query` default |
|---|---|---|---|---|
| **min** | `claude-sonnet-4-6` | - (max_depth=1) | - | `claude-haiku-4-5-20251001` |
| **default** | `claude-opus-4-7` | `claude-sonnet-4-6` | - (max_depth=2) | `claude-haiku-4-5-20251001` |
| **max** | `claude-opus-4-7` | `claude-sonnet-4-6` | `claude-haiku-4-5-20251001` | `claude-haiku-4-5-20251001` |

### Why Sonnet root in min mode

Min mode runs on small, well-defined tasks (single doc <50KB, short logs). Opus on these is overkill - Sonnet writes adequate REPL code, decomposes simple chunks, and synthesizes a few results just fine. Saves ~5x on the controller cost.

### Why Opus root in default/max

These modes run on tasks where the controller's decomposition decisions multiply. A wrong chunking choice at depth 0 wastes the entire fanout. Opus pays for itself here.

### Why Haiku at depth 2 in max mode

Default `rlms` depth routing only distinguishes depth 0 from depth 1. At depth 2 the controller would fall back to the default model (Opus) - runaway cost. So the skill instructs the depth-1 controller to pass `rlm_query(prompt, model="claude-haiku-4-5-20251001")` explicitly when it wants to recurse into Haiku-bound subtasks. This keeps the depth-2 fanout cheap.

## Wiring in `rlm_run.py`

```python
RLM(
    backend="anthropic",
    backend_kwargs={"model_name": MODE_CONFIG["root_model"]},
    other_backend="anthropic",
    other_backend_kwargs={"model_name": MODE_CONFIG["depth1_model"]},
    default_subcall_model=MODE_CONFIG["llm_query_model"],
    max_depth=MODE_CONFIG["max_depth"],
    max_iterations=MODE_CONFIG["max_iterations"],
    max_timeout=MODE_CONFIG["max_timeout"],
    max_errors=MODE_CONFIG["max_errors"],
    max_concurrent_subcalls=MODE_CONFIG["max_concurrent_subcalls"],
    environment="ipython",
    environment_kwargs={
        "kernel_mode": "subprocess",
        "cell_timeout": 30,
        "startup_timeout": 60,
        "subcall_timeout": MODE_CONFIG["max_timeout"],
    },
)
```

## Override path

Plan-step user can override any model:

```
mode=default root=claude-opus-4-7 llm_query=claude-haiku-4-5-20251001
```

Skill replays the plan with overrides and asks for re-approval.

## Cost math (rough, for plan-step estimates)

Per-mode token-cost coefficients (input + output blended, $ per 1M tokens, as of model ID resolution):

- `claude-opus-4-7`: ~$15-75
- `claude-sonnet-4-6`: ~$3-15
- `claude-haiku-4-5-20251001`: ~$0.80-4

The planner uses these to print a low/high estimate in the plan. Numbers are approximate - actual cost varies by prompt caching, batch discounts, and routing.
