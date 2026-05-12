# RLM Codex Plugin

`rlm-codex` packages a Codex skill and Python runner for Recursive Language Model workflows. It is intended for long-context work such as corpus QA, cross-document synthesis, context rot recovery, large logs, long transcripts, big code or document repositories, deep research, and chunked map/reduce analysis.

## Install

From the repository root:

```bash
codex plugin marketplace add ./openai
```

Then install the plugin from the local marketplace entry named `rlm-codex`.

The runner requires Python 3.11+ and the RLM package:

```bash
python -m pip install "rlms[ipython]"
```

Live runs also require credentials for the selected provider. For the default OpenAI backend, set `OPENAI_API_KEY` or `OPENAI_ADMIN_KEY` in the shell environment. Dry runs and health checks do not require provider credentials.

ChatGPT web subscriptions and the API platform are billed separately. A ChatGPT Pro subscription does not give a local plugin access to the OpenAI API without API quota.

## Local Model Backend

To run without OpenAI API billing, start a local OpenAI-compatible model server and point the runner at it with `--backend vllm --base-url ...`. Local servers commonly require a syntactic API key even when they do not authenticate requests; the runner supplies `api_key=EMPTY` automatically for `--backend vllm` when no key is provided.

Example with a local vLLM server:

```bash
python openai/plugins/rlm-codex/skills/rlm/scripts/rlm_run.py \
  --prompt "Question or task" \
  --context path/or/dir \
  --backend vllm \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --base-url http://localhost:8000/v1 \
  --environment local \
  --json
```

Example with an OpenAI-compatible Ollama endpoint, if Ollama is installed and serving locally:

```bash
python openai/plugins/rlm-codex/skills/rlm/scripts/rlm_run.py \
  --prompt "Question or task" \
  --context path/or/dir \
  --backend vllm \
  --model llama3.1 \
  --base-url http://localhost:11434/v1 \
  --environment local \
  --json
```

Local model quality and context limits depend on the model and serving configuration. For large RLM jobs, run `--dry-run --json` first and use a small smoke test before launching a 100+ chunk analysis.

## Health Check

```bash
python openai/plugins/rlm-codex/skills/rlm/scripts/rlm_run.py --health --json
```

Health output is JSON and includes Python version, RLM import status, supported runtime environments, IPython import status, and install guidance.

## Dry Run

Run a dry run before large directory analysis:

```bash
python openai/plugins/rlm-codex/skills/rlm/scripts/rlm_run.py \
  --prompt "Summarize the incident timeline" \
  --context ./logs \
  --batch-size 8 \
  --max-concurrent-subcalls 8 \
  --dry-run \
  --json
```

The dry run reports files, chunks, ignored directories, skipped files, estimated batches, batch size, and the recursive subcall concurrency cap.

## Live Run

```bash
python openai/plugins/rlm-codex/skills/rlm/scripts/rlm_run.py \
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

By default the runner requests `environment=ipython` with `kernel_mode=subprocess`. Some `rlms` releases do not expose an `ipython` environment or a `max_concurrent_subcalls` constructor option. In that case, the runner filters unsupported optional constructor arguments and falls back to `environment=local` when available, recording this in `fanout_plan.warnings`. Use `environment=local` only for trusted context after accepting that generated Python executes in the host process.

## Fanout

Every JSON result includes `fanout_plan`:

- `batch_size`: chunks per processing wave.
- `estimated_batches`: approximate waves needed.
- `max_concurrent_recursive_subcalls`: cap passed to `RLM(...)`.
- `environment`: selected execution environment.
- `requested_environment`: present when the runtime fell back from the requested environment.
- `model`: root model.
- `warnings`: skipped files, missing dependencies, or risky execution options.

For large tasks, summarize the dry run to the user before launching:

```text
This run will process about N chunks in batches of M, with up to K recursive subcalls at once.
```

## Context Loading

The runner supports repeated `--context` values. Each value may be a file or directory. Directory traversal ignores `.git`, `node_modules`, `.venv`, `dist`, `build`, `.rlm`, and binary files. PDFs are included only when an optional extractor such as `pypdf` is installed; otherwise they are warned and skipped.
