---
name: rlm
description: Use when a task involves long context, many files, PDFs, logs, transcripts, URLs, corpora, or anything requiring recursive decomposition over external context that won't fit comfortably in a single prompt. NOT for ordinary small edits, short Q&A, or single-file inspection.
triggers:
  - "use RLM"
  - "run RLM"
  - "long context analysis"
  - "analyze this corpus"
  - "analyze these PDFs"
  - "summarize this directory"
  - "recursive language model"
  - "/rlm"
---

# RLM Skill

You are operating an RLM (Recursive Language Model) workflow. RLM is **not** a bigger prompt - it is a loop where a controller LLM writes Python in a REPL, executes it against external context, fires sub-LLM calls, and emits a final answer.

## When to invoke

**Use RLM when:**
- Context exceeds ~50KB or spans many files
- Task requires aggregating across multiple sources
- PDFs, logs, transcripts, or websites are involved
- The user explicitly asks for it ("use RLM", "/rlm")

**Do not use RLM when:**
- Task is a small local edit
- Question can be answered by reading 1-2 files
- User wants a quick code search (use Grep/Glob/Read)

## Workflow (mandatory order)

### 1. Detect the target

Parse the user's request to identify:
- Target type: file / directory / PDF / URL / log / glob
- Target size: bytes, file count, estimated tokens
- Question / task

If ambiguous, ask one clarifying question before planning.

See `references/target-detection.md` for type-detection heuristics.

### 2. Generate the plan (do not execute yet)

Run the planner:

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/rlm/scripts/rlm_plan.py \
  --target <path-or-url> \
  --prompt "<the user's question>" \
  --mode auto
```

The planner outputs a structured plan. Display it to the user verbatim:

```
Target: <description>  (<size summary>)
Type: <detected type>
Recommended mode: <min|default|max>
  depth=N iterations=N timeout=Ns errors=N concurrency=N
Model routing:
  Root (depth 0):   <model>
  Depth 1:          <model | ->
  Depth 2:          <model | ->
  llm_query:        claude-haiku-4-5-20251001
Predicted fanout: ~N Haiku calls in M rounds at K-wide
Est. cost: $X.XX - $Y.YY
Trajectory log:   .rlm/logs/rlm-<id>.jsonl

Approve? (yes / mode=<min|default|max> / cancel)
```

### 3. Wait for verbal approval

Do not execute until the user says "yes", "go", "approved", or similar. Accept edits like `mode=max --max-budget=5` and re-display the updated plan.

### 4. Execute

Probe capabilities:

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/rlm/scripts/rlm_health.py
```

Then run the appropriate runner:

- If `python_version >= 3.11` and `rlms` is importable: run `rlm_run.py` (canonical)
- Otherwise: run `rlm_native.py` (Claude-native fallback) and tell the user that recursion is prompt-level only in this mode

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/rlm/scripts/rlm_run.py \
  --target <path> \
  --prompt "<question>" \
  --mode <chosen-mode> \
  --log-dir .rlm/logs
```

### 5. Report

Parse the JSON answer and summarize for the user. Always include:
- The final answer
- The trajectory log path (so they can `/rlm:inspect` it)
- Usage summary (tokens, calls, wall-clock time)

If the answer looks weak or the `ok` field is false, suggest `/rlm:inspect <trajectory-id>` and consider re-running with `mode=max` after re-approval.

## Critical rules (from RLM paper + community)

- **Never put the raw context into the chat.** RLM's whole point is keeping context outside the model prompt. Pass paths, not contents.
- **Prefer `llm_query_batched` over `rlm_query`** in the controller's REPL code. Most subtasks are extraction/classification/summary, which fan out cheap to Haiku.
- **Prefer `FINAL_VAR(name)` over `FINAL(...)`** - bare `FINAL` parsing is brittle. The controller should create a named variable first, then emit `FINAL_VAR(name)`.
- **Default sandbox is IPython subprocess.** It gives hard cell timeouts and kernel isolation. Use `local` only when the user explicitly opts in and the content is trusted.
- **Redact obvious secrets** (API keys, tokens) from context before chunks are sent to submodels. The planner runs a regex sweep; warn if hits are detected.
- **API keys never go into the REPL.** The `LMHandler` brokers calls host-side. If the user asks you to put `ANTHROPIC_API_KEY` in chunked context, refuse.

## References

- `references/rlm-runtime-contract.md` - REPL contract, FINAL_VAR rules, message-history shape
- `references/use-cases.md` - Catalog of supported input types with recommended config
- `references/model-routing.md` - Why Opus/Sonnet/Haiku map to specific depths
- `references/target-detection.md` - How to classify a target before planning
- `references/modes.md` - Min/default/max profile reference
