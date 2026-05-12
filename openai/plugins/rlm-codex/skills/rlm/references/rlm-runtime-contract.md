# RLM Runtime Contract

RLM keeps the raw task context outside the model prompt and exposes it inside a persistent execution environment as `context`. The controller model writes code in `repl` blocks, inspects the external context, stores intermediate results, calls submodels when useful, and returns with `FINAL(...)` or `FINAL_VAR(...)`.

The important invariant for Codex use:

```text
Do not put the whole long context into the Codex conversation.
Run the RLM runner and let the runner load context into the RLM environment.
```

The REPL environment exposes:

- `context`: the runner payload, including `context_chunks`, `context_files`, `task`, and `fanout_plan`.
- `llm_query(prompt, model=None)`: one plain model call.
- `llm_query_batched(prompts, model=None)`: parallel independent model calls.
- `rlm_query(prompt, model=None)`: a recursive child RLM call for multi-step subtasks.
- `rlm_query_batched(prompts, model=None)`: multiple child RLM calls.
- `FINAL_VAR(name)`: final answer from a REPL variable.
- `SHOW_VARS()`: inspect user-created variables.

Good controller behavior:

- Inspect `context["context_chunks"]` before answering.
- Preserve `source_path` and `chunk_id` in intermediate summaries.
- Use `llm_query_batched` for independent extraction over chunk waves.
- Use recursive RLM calls only for subtasks that need their own loop.
- Store intermediate answers in named variables.
- Return a final answer with citations or source references when useful.

RLM is best suited for corpus QA, cross-document synthesis, context rot, large logs, long transcripts, big code/document repositories, deep research, and chunked map/reduce analysis.
