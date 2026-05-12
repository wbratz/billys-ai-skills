---
name: rlm-plan
description: Generate an RLM execution plan without running it. Useful for cost estimation and dry-runs.
argument-hint: <target> "<question>" [mode]
---

# /rlm:plan

Generate a plan for an RLM run on `$1` with question `$2`. Does NOT execute.

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/rlm/scripts/rlm_plan.py \
  --target $1 \
  --prompt "$2" \
  --mode ${3:-auto}
```

Display the plan to the user. They can then call `/rlm:rlm` to actually run it, or adjust the mode/overrides.
