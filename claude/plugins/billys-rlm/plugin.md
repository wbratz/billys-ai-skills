---
name: RLM (Recursive Language Model)
description: Long-context analysis via recursive model loops over files, dirs, PDFs, logs, URLs, and corpora. Claude-only.
version: 0.1.0
author: billys
category: long-context
tags: [rlm, long-context, pdf, corpus, agents, claude]
plugin_type: claude-plugin
---

# RLM (Recursive Language Model)

Run RLM workflows from inside Claude Code. The plugin wraps the upstream [`rlms`](https://github.com/alexzhang13/rlm) package and falls back to a Claude-native orchestration mode when `rlms` isn't installed.

## What this plugin provides

- A `/rlm` slash command that targets a file, directory, PDF, URL, or log and runs an RLM loop on it.
- A planner that produces an in-chat plan (mode, models, budgets, est. cost) and waits for verbal approval.
- A runner with correct Haiku/Sonnet/Opus routing per depth.
- A Claude-native fallback so the plugin works without Python.
- A skill (`rlm`) that teaches the host agent when to delegate to RLM.

## Use cases

1. Single large document (PDF/Word/MD/TXT)
2. Directory / codebase analysis
3. Logs and transcripts (incident, chat, conversation)
4. Multi-doc corpus QA
5. Website / URL (single page or bounded crawl)
6. Structured extraction with page citations (contracts, medical, legal)
7. Notebooks / JSONL / tabular dumps
8. Multimodal docs — PDF pages as images for VLM subqueries

## Install

Drop the plugin directory into a Claude Code plugin path or marketplace, then:

```bash
claude --plugin-dir ./plugins/billys-rlm
```

Once installed, skill triggers on phrases like "use RLM", "long-context analysis", "analyze this corpus", etc. The slash command is `/rlm:rlm`.

## Configuration

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | For canonical mode | Used by `rlms` to call Claude directly. |
| `RLM_LOG_DIR` | No | Override default `.rlm/logs/` trajectory log dir. |
| `RLM_DEFAULT_MODE` | No | `min` \| `default` \| `max`. Default: `default`. |

## Operational modes

| Mode | depth | iterations | timeout | errors | concurrency |
|---|---|---|---|---|---|
| min | 1 | 6 | 120s | 2 | 4 |
| default | 2 | 12 | 300s | 4 | 8 |
| max | 3 | 20 | 900s | 6 | 12 |

See `skills/rlm/references/modes.md` for full details.

## Model routing

| Mode | Root (depth 0) | Depth 1 | Depth 2 | `llm_query` |
|---|---|---|---|---|
| min | claude-sonnet-4-6 | — | — | claude-haiku-4-5-20251001 |
| default | claude-opus-4-7 | claude-sonnet-4-6 | — | claude-haiku-4-5-20251001 |
| max | claude-opus-4-7 | claude-sonnet-4-6 | claude-haiku-4-5-20251001 | claude-haiku-4-5-20251001 |

## Notes

- Canonical mode requires Python 3.11+ and the `rlms` package. The runner validates both and prints clear remediation if missing.
- Default sandbox is IPython subprocess for hard cell timeouts and namespace isolation.
- Trajectory logs are JSONL under `.rlm/logs/` and gitignored by convention.
- Final-answer parsing is brittle in RLM by design — the skill instructs the controller to prefer `FINAL_VAR(name)` over raw `FINAL(...)`.
