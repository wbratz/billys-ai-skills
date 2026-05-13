# rlm-auto

**Passive Recursive-Language-Model routing for Claude Code.** Install once, then just use Claude Code normally — when a task is large/cross-document/corpus-shaped, this plugin silently routes it through RLM, surfaces an honest cost/speed/accuracy estimate, and grades its own decision afterwards. The grading log is local-only and is meant to be dogfooded back into the routing heuristic.

## Why install

- **Stop thinking about when to use RLM.** A `UserPromptSubmit` hook classifies each task in <100 ms and tells Claude when RLM is the right tool.
- **No "are you sure?" prompts under a budget cap.** Below a configurable threshold (default $0.50), RLM auto-executes. Above, you're asked once.
- **Per-decision cost/speed/accuracy estimate** rendered into the answer so you always know what you spent (and what you saved vs. direct execution).
- **Local-only decision log + post-hoc grader.** Every routing decision (RLM or not) is graded against the task's actual tool usage. `/rlm-auto:status` shows accuracy, false-positive rate, and savings to date — never leaves your machine.
- **Designed to be dogfooded.** The grader's "why-wrong" reasons feed directly into threshold tuning via `/rlm-auto:config`.

## What you don't need to know
- When inputs are RLM-shaped (the classifier handles it).
- Mode selection (planner picks `min`/`default`/`max` by target size).
- Whether `rlms` is installed (falls back to the native Claude runner automatically).

## Requirements
- The `rlm` plugin must be installed and on the same marketplace (`claude plugin install rlm`).
- Python 3.10+ (`py -3` on Windows or `python3` on Unix). All hook scripts are stdlib-only.
- Optional: `rlms` package for the canonical Python-REPL controller. Without it, the native fallback runs (prompt-level recursion only).

## Quick start

```bash
claude plugin install rlm-auto
# Add the two hooks to your user-level settings.json (sample provided
# at hooks/settings.json.example after install).
/rlm-auto:status   # show the decision log so far
```

After that you just use Claude Code normally. Try:

> "summarize every PDF under ./reports/ for the Q3 review"

The hook flags the prompt as RLM-shaped, the `rlm-auto` skill plans the run, sees an est. cost of $0.31, auto-executes (below the $0.50 cap), and prints the answer plus a footer:

```
[rlm-auto] used RLM (mode=default, est $0.18-$0.31, est savings vs direct ~60%, log: .rlm/decisions.jsonl)
```

## Tradeoffs we're honest about

- The classifier is heuristic. It will misroute sometimes. The eval loop exists precisely to surface those cases so you can tune thresholds.
- RLM has higher cost variance than a single Opus call. The auto-approve cap is the protection — set it to what you're comfortable burning on a misclassification.
- "Saves time" claims in the estimate are based on the source paper plus your local history; they are projections, not measurements.

See `README.md` for installation, settings, threshold tuning, and the dogfood workflow.
