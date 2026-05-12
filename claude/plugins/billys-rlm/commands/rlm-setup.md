---
name: rlm-setup
description: Check prerequisites for the RLM plugin (Python 3.11+, rlms package, API key, etc.) and report what's missing with exact install commands.
---

# /rlm:setup

Run the setup check and surface the results to the user.

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/rlm/scripts/setup.py
```

If `python` resolves to <3.11, fall back to `py -3` (Windows) or `python3.11` / `python3.12` (Unix).

## Interpreting the output

The script prints a status table. For each missing/warn item, it prints the exact command the user should run. **Do not run those commands automatically.** Display them to the user and let them choose what to install.

After displaying the status table:

- If canonical runner is READY (exit 0): tell the user `/rlm:rlm` will use the canonical RLM loop.
- If canonical runner is NOT ready but Python is OK (exit 1): tell the user `/rlm:rlm` will fall back to the native Claude orchestration mode. Mention the tradeoff (no Python REPL, prompt-level recursion only).
- If Python is missing (exit 2): tell the user they need to install Python 3.11+ before anything else works.

## What setup checks

| Check | Required for |
|---|---|
| Python 3.11+ | Canonical runner |
| `rlms` package | Canonical runner |
| `ipykernel` | Default IPython subprocess sandbox |
| `pypdf` | PDF loader |
| `ANTHROPIC_API_KEY` | Canonical runner (API calls) |
| `.rlm/logs/` writable | Trajectory logs |
| `.gitignore` contains `.rlm/` | Best practice — keeps logs out of VCS |

## Manual full install (for reference)

If the user wants to install everything at once:

```bash
python -m pip install --upgrade rlms ipykernel pypdf
export ANTHROPIC_API_KEY='sk-ant-...'      # or $env:ANTHROPIC_API_KEY on Windows
echo '.rlm/' >> .gitignore
```
