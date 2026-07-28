# billys/rlm

Recursive Language Model plugin for Claude Code.

Long-context analysis without stuffing the whole context into the model prompt. Files, directories, PDFs, logs, URLs, and corpora go through a loop where a controller LLM writes Python in a REPL, executes against external context, fires parallel `llm_query` subcalls to Haiku, and synthesizes a final answer.

## Quick start

```bash
# Option A: add the marketplace once, then install
claude plugin marketplace add <path-or-url-to-the-claude-directory>
claude plugin install rlm

# Option B: load this plugin directly
claude --plugin-dir ./plugins/billys-rlm

# First time only: check prereqs and follow setup instructions
/rlm:rlm-setup

# Then run RLM
/rlm:rlm ./docs/ "What does this codebase do?"
```

The skill plans the run, shows you the plan (mode, models, budgets, est. cost), and waits for verbal approval before executing.

## Install prerequisites

`/rlm:rlm-setup` will check and report:

| Check | Required for |
|---|---|
| Python 3.11+ | Canonical runner |
| `rlms` package | Canonical runner |
| `ipykernel` | Default IPython subprocess sandbox |
| `pypdf` | PDF loader |
| `ANTHROPIC_API_KEY` | Canonical runner (API calls) |
| `.rlm/logs/` writable | Trajectory logs |

If any are missing, the command shows the exact install line. Nothing is installed automatically. If `rlms` or Python 3.11+ are unavailable, the plugin falls back to a Claude-native orchestration mode (prompt-level recursion, no REPL).

## What it does

A controller model (Opus 4.7) gets a small system prompt and access to a Python REPL where your context lives in a `context` variable. It writes code to chunk and inspect the context, fires batched `llm_query` calls to Haiku 4.5 for extraction/classification/summary, and emits a final answer when done.

This is **breadth, not depth** - parallel Haiku fanout beats deeper recursive trees on cost, latency, and quality. The plugin defaults reflect that.

## Modes

Pick at plan time, or let the planner auto-recommend based on target size.

| Mode | When | depth | iter | timeout | conc |
|---|---|---|---|---|---|
| **min** | Single doc / cheap extraction | 1 | 6 | 120s | 4 |
| **default** | Most corpus QA | 2 | 12 | 300s | 8 |
| **max** | Deep hierarchical synthesis | 3 | 20 | 900s | 12 |

## Files

```
plugin.md              Marketplace entry
.claude-plugin/        Claude Code package manifest
skills/rlm/            The skill (SKILL.md + references + scripts)
commands/              Slash commands (/rlm, /rlm:plan, /rlm:inspect)
agents/                Sub-agent for autonomous RLM runs
.mcp.json              Stub for v0.2 MCP server
```

## Requirements

- **Canonical mode:** Python 3.11+, `pip install rlms`, `ANTHROPIC_API_KEY` set.
- **Native fallback:** none. Works out of the box but recursion is prompt-level only.

## Status

v0.1, experimental. A separate Codex implementation is available in this
repository under `openai/plugins/rlm-codex/`.
