---
name: rlm
description: Run an RLM (Recursive Language Model) workflow on a target — file, directory, PDF, URL, log, or corpus. Plans first, awaits approval, then executes.
argument-hint: <target> "<question>"
---

# /rlm

Run RLM over `$1` answering `$2`.

This command is a thin wrapper that invokes the `rlm` skill. The skill:

1. Detects target type via `rlm_plan.py`
2. Emits a plan (mode, models, budget, est. cost) in chat
3. Waits for verbal approval ("yes" / "mode=X" / "cancel")
4. Probes capabilities via `rlm_health.py`
5. Executes `rlm_run.py` (canonical, if Python 3.11+ and `rlms` are available) or `rlm_native.py` (fallback)
6. Reports the answer + trajectory log path

## Usage

```
/rlm:rlm ./docs/ "What does this codebase do?"
/rlm:rlm report.pdf "Extract all numeric claims with page citations"
/rlm:rlm https://example.com/post "Summarize the author's argument"
/rlm:rlm server.log "What caused the 14:32 outage?"
```

## After invocation

Follow the skill protocol in `skills/rlm/SKILL.md` exactly. Do not skip the planning step.
