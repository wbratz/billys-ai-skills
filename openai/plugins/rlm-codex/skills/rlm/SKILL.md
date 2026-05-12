---
name: rlm
description: Use when the user explicitly says "use RLM" or a task needs long-context recursive decomposition across many files, logs, transcripts, corpora, PDFs, or documents. Do not use for narrow edits, small single-file analysis, ordinary repo search, or tasks with no external context.
---

# RLM

Use this skill to delegate long-context analysis to a Recursive Language Model runner. RLM is useful for corpus QA, cross-document synthesis, context rot recovery, large logs, long transcripts, big code or document repos, deep research, and chunked map/reduce analysis.

## When To Use

Use RLM when:

- The user explicitly asks to "use RLM".
- The task has many or large context files that should not be pasted into the Codex conversation.
- The answer requires synthesis across documents, logs, transcripts, or many repository areas.
- A recursive map/reduce workflow over chunks would reduce context pressure.
- An agent or another skill decides the task needs long-context recursive decomposition.

Avoid RLM when:

- A normal `rg`, file read, or focused edit is enough.
- The task is a narrow code change in a small set of files.
- The context is a small single file.
- There is no external context to analyze.

## Runner

The runner script is adjacent to this skill:

```bash
python skills/rlm/scripts/rlm_run.py \
  --prompt "Question or task" \
  --context path/or/dir \
  --backend openai \
  --model gpt-5.4 \
  --environment ipython \
  --batch-size 8 \
  --max-concurrent-subcalls 8 \
  --max-depth 2 \
  --max-iterations 12 \
  --max-timeout 300 \
  --json
```

If the plugin is installed in a Codex cache, resolve the absolute path of this `SKILL.md` file and run the adjacent `scripts/rlm_run.py`.

Run `--health` before first use when the environment is unknown:

```bash
python skills/rlm/scripts/rlm_run.py --health --json
```

Live runs require provider credentials for the selected backend. For the default OpenAI backend, set `OPENAI_API_KEY` or `OPENAI_ADMIN_KEY` in the shell environment. Do not put provider keys in prompts, context files, or generated logs.

ChatGPT web subscriptions and the API platform are billed separately. A ChatGPT Pro subscription does not give a local plugin API quota. To run without OpenAI API billing, use a local OpenAI-compatible model server and pass `--backend vllm --base-url http://localhost:<port>/v1`. The runner supplies a dummy `api_key=EMPTY` for `--backend vllm` when no key is provided.

Run `--dry-run` before expensive large-directory tasks so the user can see fanout:

```bash
python skills/rlm/scripts/rlm_run.py \
  --prompt "Summarize the incident timeline" \
  --context ./logs \
  --dry-run \
  --json
```

Surface the dry-run fanout in plain language before a large live run:

```text
This run will process about N chunks in batches of M, with up to K recursive subcalls at once.
```

## Defaults

- `backend=openai`
- `model=gpt-5.4`
- `environment=ipython`
- `kernel_mode=subprocess`
- `batch_size=8`
- `max_concurrent_subcalls=8`
- `max_depth=2`
- `max_iterations=12`
- `max_timeout=300`
- `max_errors=4`

Prefer subprocess IPython. Use same-process local execution only when the user explicitly accepts that the context is trusted, because local execution can run host Python code.

Some `rlms` runtime versions do not expose `environment=ipython` or the `max_concurrent_subcalls` constructor argument. The runner detects supported constructor options at runtime, treats unsupported subcall caps as advisory, and falls back from `ipython` to `local` when that is the only available environment. Surface any resulting `fanout_plan.warnings` to the user.

## Operating Rules

- Keep large raw context in files or directories; do not paste it into chat.
- Use repeated `--context` for multiple roots.
- For directories, the runner ignores `.git`, `node_modules`, `.venv`, `dist`, `build`, `.rlm`, and binary files.
- Ask RLM to use `llm_query_batched` for independent chunk extraction and `rlm_query` or `rlm_query_batched` only when a subtask needs multi-step reasoning.
- Treat `--batch-size` as the chunk-processing wave size.
- Treat `--max-concurrent-subcalls` as the recursive child RLM fanout cap.
- Never put provider keys in prompts, context files, or generated logs.
- Inspect trajectory logs when an answer looks weak or incomplete.

See `references/rlm-runtime-contract.md` and `references/fanout-and-safety.md` for the runtime contract and safety notes.
