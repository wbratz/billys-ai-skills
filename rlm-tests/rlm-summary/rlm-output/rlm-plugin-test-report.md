# RLM Codex Plugin Test Report

## Scope

Goal: test the installed `rlm-codex` plugin against the arXiv HTML paper "Recursive Language Models" and produce audience-specific meeting summaries.

Source URL: https://arxiv.org/html/2512.24601v2

Local context file: `rlm-tests/rlm-summary/rlm-output/recursive-language-models.html`

## What Worked

Health check passed for the cached installed runner:

- Python executable: `C:\dev\billys-ai-skills\.venv-rlm\Scripts\python.exe`
- Python version: `3.14.5`
- `rlms` importable: yes
- `rlms` version: `0.1.1`
- IPython packages importable: yes

The arXiv HTML was downloaded successfully after allowing network access.

Initial dry run over the paper succeeded:

- Files: 1
- Characters loaded: 1,317,390
- Chunks: 115
- Batch size: 8
- Estimated batches: 15
- Recursive subcall cap requested by runner: 8
- Warnings: none before runtime compatibility checking was added

After the runner fix, dry run also reports runtime compatibility warnings before launch:

- Requested environment: `ipython`
- Effective environment: `local`
- Warning: installed `rlms` does not support `environment=ipython`
- Warning: installed `rlms` does not accept `max_concurrent_subcalls`, so the cap is advisory with this runtime

The local plugin source tests pass after the compatibility patch:

```text
openai/plugins/rlm-codex/tests/test_rlm_run.py ...... [100%]
6 passed
```

## What Failed

The cached installed runner failed on the first live run:

```text
RLM.__init__() got an unexpected keyword argument 'max_concurrent_subcalls'
```

Root cause: the plugin runner expects a newer or different `rlms` constructor API than the installed `rlms 0.1.1` runtime exposes. The installed `RLM(...)` signature does not accept `max_concurrent_subcalls`, and its environment choices are `local`, `docker`, `modal`, `prime`, `daytona`, and `e2b`, not `ipython`.

I patched the repo-local runner at:

`openai/plugins/rlm-codex/skills/rlm/scripts/rlm_run.py`

The patch filters unsupported optional constructor arguments and records an environment fallback warning if `ipython` is requested but unsupported. I then copied the same patched runner into the cached installed plugin path:

`C:\Users\willi\.codex\plugins\cache\billys-openai-marketplace\rlm-codex\0.1.0\skills\rlm\scripts\rlm_run.py`

After patching the cached installed runner, the installed-cache dry run still succeeds with the same 115-chunk fanout plan and now surfaces the runtime fallback warnings. A live smoke attempt got past the constructor issue, then failed because no provider credential is available:

```text
Missing credentials. Please pass an api_key, workload_identity, admin_api_key, or set the OPENAI_API_KEY or OPENAI_ADMIN_KEY environment variable.
```

Credential names checked in the shell did not show supported provider keys for OpenAI, Anthropic, Gemini, Google, Portkey, OpenRouter, or Azure OpenAI.

## How To Rerun

Set a supported provider credential in the shell, without putting the key into prompts, logs, or context files. For OpenAI, set `OPENAI_API_KEY` or `OPENAI_ADMIN_KEY`.

Then rerun:

```powershell
python openai\plugins\rlm-codex\skills\rlm\scripts\rlm_run.py `
  --prompt "Analyze this paper for audience-specific RLM summaries." `
  --context rlm-tests\rlm-summary\rlm-output\recursive-language-models.html `
  --backend openai `
  --model gpt-5.4 `
  --environment ipython `
  --batch-size 8 `
  --max-concurrent-subcalls 8 `
  --max-depth 2 `
  --max-iterations 12 `
  --max-timeout 300 `
  --log-dir rlm-tests\rlm-summary\rlm-output\.rlm `
  --json
```

Expected behavior with the current source and cached-runner patch: if the installed runtime still does not support `ipython`, the runner will fall back to `local` and include that in `fanout_plan.warnings`.

## Summary Artifact Provenance

Because the live model-backed RLM run was blocked by missing credentials, the meeting summaries in this folder are grounded in the downloaded arXiv HTML and direct source review, not in a completed RLM response. The plugin test artifacts above should still be useful: they identify the runtime API mismatch and the credential blocker required for a full live RLM test.
