# RLM Runtime Contract

Reference for the host agent on how the RLM loop behaves at runtime. Sourced from the upstream `rlms` package (commit 03a1774, 2026-05-11).

## The loop

```
RLM.completion(prompt, root_prompt=None):
  if depth >= max_depth: return _fallback_answer(prompt)
  for i in range(max_iterations):
    check_timeout()
    maybe_compact_history()
    response = lm_handler.completion(current_prompt)
    for block in find_code_blocks(response):  # ```repl ... ``` blocks
      result = environment.execute_code(block)
    if final_answer in response: return RLMChatCompletion
    message_history.extend(format_iteration(response, code_results))
  return default_answer_from_message_history()
```

## What the controller sees per turn

1. The RLM system prompt (provider-tuned).
2. A metadata message — context type and character lengths only.
3. Its own previous response.
4. For each executed `repl` block: a user message with the code, stdout/stderr, and a list of bound variable names.

The controller **does not see the raw `context` payload.** It must inspect `context` from the REPL or pass chunks to submodels.

## REPL globals the controller can call

```python
context             # the loaded context payload
context_0, context_1, ...   # individual context items if list-typed
history             # message history (for compaction)
llm_query(prompt, model=None)
llm_query_batched(prompts, model=None)   # parallel, order-preserving
rlm_query(prompt, model=None)            # child RLM with its own loop
rlm_query_batched(prompts, model=None)
FINAL_VAR(name)                          # final answer from a named var
SHOW_VARS()                              # debug helper
# plus custom tools provided by the runner
```

## Final-answer protocol

Two ways to terminate:

1. `FINAL(<answer text>)` — bare final, brittle parsing.
2. `FINAL_VAR(name)` — emit the value bound to variable `name`. **Preferred.**

The skill instructs the controller to always create a named variable first and emit `FINAL_VAR(name)` for stability.

## Depth-based routing

`rlms` natively routes by depth:

- **Default client** for depth 0 (and depth 2+ unless overridden).
- **`other_backend_client`** for depth 1.

Depth 2+ falls back to the default model unless the executing code passes an explicit `model=` arg. Our `max` mode instructs the controller to pass `model="claude-haiku-4-5-20251001"` for `rlm_query` calls at depth 2.

## Stop conditions

- `FINAL` / `FINAL_VAR` emitted
- `max_iterations` reached → returns best-effort from message history
- `max_timeout` hit between iterations
- `max_errors` consecutive REPL errors
- `max_budget` exceeded (if set)

## Environment choices

| Environment | Use when |
|---|---|
| `local` | Trusted code, max speed, same-process `exec`. Not a security boundary. |
| `ipython` (subprocess) | **Default for this plugin.** Hard cell timeout, kernel isolation, late-subcall attribution fixed. |
| `ipython` (in-process) | Faster than subprocess but no hard timeouts on non-Unix. |
| `docker` / cloud sandboxes | Adversarial content. Note: child `rlm_query` is not fully wired in these envs in upstream rlms (use `local`/`ipython` if you need depth>1). |

## Known limitations to respect

- `LocalREPL` has `open()` and `__import__` — it's **not** a sandbox.
- Compaction only works in environments that implement `append_compaction_entry` (currently `local` in upstream). Don't enable `compaction=True` with IPython without verifying.
- `socket_recv` in `comms_utils.py` reads the 4-byte length prefix with a single `recv(4)` — can fail on partial TCP reads. Upstream hardening pending.
- Provider clients and usage counters may not be thread-safe at high parallelism. Our `max` mode (concurrency=12) is the upper bound we've audited.
- `RLM._fallback_answer` returns a raw string when `depth >= max_depth` — the runner normalizes this.
