# billys/rlm-auto

Passive RLM routing + cost/speed/accuracy estimator + local-only decision evaluator. Companion to the [`rlm`](../billys-rlm/) plugin.

> **TL;DR.** Install both plugins (this one + `rlm`, which is required), copy the hooks block from `hooks/settings.json.example` into your `~/.claude/settings.json`, and use Claude Code normally. When a task is RLM-shaped, the plugin auto-routes through RLM under a budget cap (deterministic - checked by `scripts/check_cap.py`, not honor-system). Every decision (route OR pass-through) is graded locally. `/rlm-auto:status` shows you how well the heuristic is doing and what it cost.

> **Dependency.** This plugin invokes the public `/rlm:rlm-plan` and `/rlm:rlm` slash commands from the `rlm` plugin. If `rlm` is not installed, the auto-routing skill aborts cleanly and the turn proceeds as if `rlm-auto` weren't installed.

---

## Install

```bash
# 1. Add the marketplace if not already
claude plugin marketplace add <path-or-url-to-the-claude-directory>

# 2. Install the base RLM plugin (required dependency)
claude plugin install rlm

# 3. Install rlm-auto
claude plugin install rlm-auto

# 4. Copy the two hook lines from this plugin's hooks/settings.json.example
#    into your ~/.claude/settings.json (the "hooks" object). Restart Claude Code.
```

Verify with:

```bash
/rlm-auto:status
```

If the hook is wired correctly the status command shows `decisions logged: 0` and the path to the local log.

---

## How it works (three layers)

```
User prompt
   │
   ▼
[UserPromptSubmit hook]   <-- hooks/user_prompt_submit.py
   - regex scan for RLM signals: "all/every/audit/across", glob patterns
   - stat() any paths or URLs in the prompt
   - emit <system-reminder> with verdict + classification + estimate
   │
   ▼
Claude reads the prompt + the reminder
   │  (routing decision happens here, guided by rlm-auto skill)
   ▼
verdict = "rlm"           verdict = "direct"     verdict = "ambiguous"
   ▼                         ▼                      ▼
rlm-auto skill            normal tools           rlm-auto skill runs
  1. rlm_plan.py            (Read/Grep/Edit)      planner only, shows
  2. if est_cost.high                              one-line estimate
     <= cap: auto-run                              and lets Claude decide
  3. else: ask once
  4. print answer + footer
   │
   ▼
[PostToolUse hook]        <-- hooks/post_tool_use.py
   - records tool-call metadata (sizes, files touched) to decision log
   │
   ▼
[Stop hook]               <-- hooks/post_tool_use.py with --on-stop
   - evaluator grades the decision and appends "verdict_grade" to log
```

The three running layers are all local. No telemetry, no network calls from the hooks themselves.

---

## What gets logged

`~/.rlm/decisions.jsonl` by default (one entry per decision, append-only). Override the location via `log_path` in `~/.rlm/auto-config.json` - e.g. `"log_path": "~/work/rlm-decisions.jsonl"`. Shape:

```json
{
  "ts": "2026-05-13T14:02:11Z",
  "session_id": "ccab12...",
  "prompt_hash": "9f3e...",
  "prompt_len": 187,
  "signals": ["dir ./reports = 14.2 MB", "kw:every", "kw:summarize"],
  "verdict": "rlm",
  "auto_approved": true,
  "estimate": {
    "rlm_cost_low": 0.18, "rlm_cost_high": 0.31,
    "direct_cost_low": 0.90, "direct_cost_high": 1.40,
    "savings_pct": 70,
    "accuracy_uplift_pp": 12.5,
    "source": "paper:browsecomp-plus + local-history"
  },
  "outcome": {
    "ran": "rlm",
    "actual_cost_est_usd": 0.22,
    "wallclock_s": 142,
    "tool_calls": 6,
    "bytes_read_directly": 0
  },
  "grade": {
    "verdict_grade": "correct",
    "reason": "input_size=14.2MB exceeds 50KB threshold; direct would have read >12 files",
    "false_positive": false,
    "false_negative": false,
    "needs_review": false
  }
}
```

The grader uses heuristics, not ground truth. When it marks `needs_review: true`, that's the dogfood signal - review those entries, decide if the heuristic was wrong, and tune.

---

## Tuning (the dogfood loop)

1. Run Claude Code normally for a week.
2. `/rlm-auto:status` - see false-positive rate, false-negative rate, total spend, total estimated savings.
3. `/rlm-auto:config` to adjust:
   - `min_size_bytes` (default 50 KB) - the threshold below which RLM is overkill.
   - `min_file_count` (default 5) - fewer than this and we route direct.
   - `auto_approve_cap_usd` (default 0.50) - RLM auto-runs below this; asks above.
   - `kw_positive`, `kw_negative` - keyword lists.
   - `enabled` - kill switch.

Settings live in `~/.rlm/auto-config.json`. The defaults file (`config/defaults.json`) ships with the plugin.

---

## Estimates are projections, not measurements

The estimator pulls from two sources:
1. **The RLM paper** - accuracy/cost numbers from BrowseComp-Plus and OOLONG (`source: "paper:..."`).
2. **Your local decision log** - once you have >20 RLM decisions, the median measured cost replaces the paper number (`source: "local-history"`).

Until you have local history, treat the savings number as a published-benchmark projection.

---

## Files

```
.claude-plugin/plugin.json     Manifest
plugin.md                      Marketplace pitch
README.md                      This file
hooks/                         User-installable hook scripts
  user_prompt_submit.py        Classifier hook (cheap, deterministic)
  post_tool_use.py             Telemetry + on-stop grader
  settings.json.example        Copy-paste block for ~/.claude/settings.json
scripts/                       Logic shared by hooks + skills
  classify.py                  Signal detection (paths, keywords, sizes)
  estimate.py                  Cost/speed/accuracy projection
  evaluate.py                  Post-hoc decision grader
  decision_log.py              JSONL writer/reader
skills/                        Skills Claude auto-loads
  rlm-auto/SKILL.md            Routing logic
  rlm-estimate/SKILL.md        Estimate formatter for the answer footer
  rlm-eval/SKILL.md            Grader workflow for /rlm-auto:status
commands/                      Slash commands
  rlm-auto-status.md           /rlm-auto:status
  rlm-auto-config.md           /rlm-auto:config
  rlm-auto-disable.md          /rlm-auto:disable
config/
  defaults.json                Default thresholds
```

---

## Privacy

What stays local-only:
- The decision log at `~/.rlm/decisions.jsonl` (or wherever `log_path` in `~/.rlm/auto-config.json` points). Delete it any time.
- All grades, accuracy metrics, and cumulative cost / savings totals.
- Prompts are hashed (SHA-256, first 16 hex chars) by default. Set `log_full_prompts: true` in `~/.rlm/auto-config.json` to opt in to verbatim local storage.
- The hook scripts themselves never open a network socket.

What the hook *does* send into the next API call (this is by design - it's how Claude sees the verdict):
- The injected `<system-reminder>` includes the classification verdict, the matched signals (e.g. `dir ./reports = 14.2 MB`, `kw:every`), the score, and the cost/savings estimate. That reminder is part of the prompt and therefore travels with the next request to Anthropic, like any other prompt content.
- If you don't want path names or detected keywords leaving the machine, set `enabled: false` via `/rlm-auto:disable --persistent`.

---

## Status

v0.1 - experimental. The classifier is intentionally conservative (favors false negatives over false positives) so the worst case is "Claude does what it would have done anyway".
