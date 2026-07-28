# RLM Codex

Long-context recursive analysis for OpenAI Codex.

The plugin packages an RLM skill and a tested Python runner for questions that
span large repositories, document collections, logs, transcripts, or research
corpora. It includes health checks, dry-run planning, bounded fanout, ignored
path rules, and support for OpenAI-compatible local model servers.

## Quick check

After installing the plugin dependencies:

```bash
python skills/rlm/scripts/rlm_run.py --health --json
```

Preview a run before spending tokens or executing generated analysis:

```bash
python skills/rlm/scripts/rlm_run.py \
  --prompt "Summarize the incident timeline" \
  --context ./logs \
  --dry-run \
  --json
```

For installation, backends, live-run options, and safety details, read the
[complete guide](../../docs/rlm-codex.md).
