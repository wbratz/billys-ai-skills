---
name: rlm-inspect
description: Inspect an RLM trajectory log to understand iteration-by-iteration what the controller and subcalls did.
argument-hint: <trajectory-id-or-path>
---

# /rlm:inspect

Read the JSONL trajectory log for an RLM run and summarize:

- Total iterations
- Each iteration's code blocks and outputs (truncated)
- Subcalls made (model, prompt summary, response summary, duration)
- Final answer source (FINAL vs FINAL_VAR, which variable)
- Warnings (timeouts, retries, parse failures)
- Token usage breakdown by model

## Usage

```
/rlm:inspect a3f9b2c1
/rlm:inspect .rlm/logs/rlm-a3f9b2c1.jsonl
```

If only an ID is passed, look in `.rlm/logs/rlm-<id>.jsonl`.

The host agent should read the JSONL file line-by-line and produce a structured markdown summary. Highlight any iteration that looks anomalous (very long, errors, no progress).
