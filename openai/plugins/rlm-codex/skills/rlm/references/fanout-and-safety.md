# Fanout And Safety

The runner reports a `fanout_plan` before and after live runs:

- `batch_size`: maximum context chunks per processing wave.
- `estimated_batches`: approximate chunk waves to process.
- `max_concurrent_recursive_subcalls`: cap for child RLM calls.
- `environment`: execution environment selected for generated code.
- `requested_environment`: present when the runtime fell back from the requested environment.
- `model`: root model used by RLM.
- `warnings`: skipped files, missing dependencies, and risky options.

Before expensive directory runs, use `--dry-run --json` and tell the user:

```text
This run will process about N chunks in batches of M, with up to K recursive subcalls at once.
```

Execution guidance:

- Prefer `environment=ipython` with `kernel_mode=subprocess`.
- Use `environment=local` only for trusted content and after explicit user acceptance.
- If the installed `rlms` runtime does not support `environment=ipython`, the runner may fall back to `environment=local` and emit a warning. Treat that as a safety-relevant change, not a cosmetic one.
- Keep `max_depth=2` for normal decomposition; raise it only with a strict budget and timeout.
- Keep `max_concurrent_subcalls` bounded to protect provider rate limits and local resources.
- Some `rlms` runtime versions do not accept `max_concurrent_subcalls`; the runner reports this and treats the cap as advisory.
- Use `--max-timeout`, `--max-iterations`, and `--max-errors` on every live run.

The runner does not install dependencies. If health fails, install in a Python 3.11+ environment:

```bash
python -m pip install "rlms[ipython]"
```

Provider and local-model guidance:

- The default `openai` backend requires OpenAI API quota; ChatGPT web subscriptions do not provide local plugin API quota.
- To avoid OpenAI API billing, use a local OpenAI-compatible server with `--backend vllm --base-url http://localhost:<port>/v1`.
- The runner supplies `api_key=EMPTY` automatically for `--backend vllm` when no key is provided, which is suitable for unauthenticated local servers.
- Local models need enough context length for the RLM root prompt and subcalls. Start with a small smoke test before running large corpora.
