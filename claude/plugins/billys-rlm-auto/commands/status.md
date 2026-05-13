---
name: status
description: Show the local decision log summary - how often the router routed RLM vs direct, how often it was right, and what it cost / saved. Reads ~/.rlm/decisions.jsonl. Never sends anything off the machine.
---

# /rlm-auto:status

Invoke the `rlm-eval` skill to produce the dogfood report:

1. Grade any ungraded rows in `~/.rlm/decisions.jsonl`.
2. Print a summary with counts, accuracy, and cumulative cost / savings.
3. List the review queue (rows the grader was not confident about) and
   walk the user through them if they want.
4. Offer tuning recommendations only if the data supports them.

## Usage

```
/rlm-auto:status
```

## Expected output

```
rlm-auto status (log: ~/.rlm/decisions.jsonl)
  Decisions logged:        42
  Correct:                 36  (86%)
  False positive (RLM):    2   (5%)
  False negative (direct): 3   (7%)
  Indeterminate / unclear: 1
  Needs human review:      4

  Spent on RLM (cumulative):     $4.32
  Realized savings vs direct:    $9.18

  Review queue: 4 entries. Want me to walk them with you? (yes/no)
```

If `Decisions logged: 0`, the hook is probably not wired up. Tell the user
to copy `hooks/settings.json.example` into `~/.claude/settings.json` and
restart Claude Code.
