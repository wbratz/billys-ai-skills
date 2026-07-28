---
name: rlm-auto
description: >-
  Routes long-context, cross-document, and corpus tasks through the rlm plugin
  when the UserPromptSubmit hook flags them as RLM-shaped. Invoke only when an
  rlm-auto system reminder is present.
triggers:
  - "rlm-auto: this task looks RLM-shaped"
  - "rlm-auto: this task is borderline"
  - "rlm-auto routing"
---

# rlm-auto routing skill

You only run this skill when a `rlm-auto:` system reminder appears earlier in
the turn. The reminder will tell you:
- the verdict (`rlm` / `ambiguous` / `direct`)
- the signals
- the cost estimate
- the decision_id
- the auto-approve cap

This skill never invokes a sibling plugin's scripts by path. It invokes the
public slash commands the user already has registered (`/rlm:rlm-plan` and
`/rlm:rlm`) so the rlm plugin's install location stays opaque.

## Workflow when verdict = rlm

1. **Plan the run silently.** Invoke the planning slash command:

   ```
   /rlm:rlm-plan <target-from-prompt> "<user's question>"
   ```

   The command outputs the same Markdown + fenced JSON block as
   `rlm_plan.py`. Parse the JSON block.

2. **Check the cap deterministically.** Pipe the plan's JSON into the
   bundled cap-check helper. Do not eyeball the math:

   ```bash
   py -3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_cap.py" --plan-json '<plan-json>'
   ```

   The script reads `~/.rlm/auto-config.json` for `auto_approve_cap_usd`,
   compares it to `plan.est_cost_usd.high`, and prints one line:
   `decision=auto_approve` or `decision=ask reason=<reason>`. Exit code
   matches: 0 for auto-approve, 1 for ask. Trust the exit code.

3. **If decision=ask**, emit exactly one line and wait:

   > rlm-auto: estimated cost up to **$X.XX** exceeds the auto-approve cap (**$Y.YY**). Run anyway? (yes/no)

   Do not paraphrase, do not ask follow-ups. On `yes`, proceed; on
   anything else, fall back to a normal direct flow.

4. **Execute via the public slash command.** Once approved (auto or
   explicit), invoke:

   ```
   /rlm:rlm <target> "<question>"
   ```

   That command handles health probe + native fallback automatically.

5. **Produce the answer.** Render the final answer to the user. Append
   exactly ONE footer line built from the estimate the system reminder
   gave you (or re-derived via the `rlm-estimate` skill):

   ```
   [rlm-auto] used RLM mode=<min|default|max> (est $X.XX-$Y.YY,
   ~Z% vs direct, +Wpp acc projected; log: .rlm/logs/<id>.jsonl;
   decision: <decision_id>)
   ```

   This footer is the user-visible transparency signal. Do NOT skip it
   unless `show_footer: false` is set in `~/.rlm/auto-config.json`.

6. **Attach an accurate outcome.** If the runner reported a real cost
   figure, write it to the decision log so the evaluator grades against
   reality, not the projection:

   ```bash
   py -3 "${CLAUDE_PLUGIN_ROOT}/scripts/decision_log.py" attach-outcome \
     --decision-id <decision_id> \
     --outcome-json '{"ran":"rlm","actual_cost_est_usd":0.22,"rlm_fanout":12,"tool_calls":N}'
   ```

   Otherwise the Stop hook fills in what it can from session telemetry.

## Workflow when verdict = ambiguous

Do not auto-route. Decide for yourself based on the user's actual question:
- If the question requires reasoning *across* the inputs (compare,
  aggregate, audit, summarize the whole), invoke `/rlm:rlm-plan` and
  follow the same cap-check + execute flow as above.
- If it's a lookup-style question on one of the inputs, proceed normally.

Either way, no footer is required when going direct.

## Workflow when verdict = direct

Do nothing. The hook already logged the decision; the evaluator will
grade it on session end.

## Critical rules

- **Never explain RLM unless asked.** This skill is meant to be invisible.
  The one-line footer is the only transparency signal.
- **Never put the user's raw input into your chat context.** Pass paths
  to the RLM scripts. RLM's whole point is to keep big context outside
  the prompt.
- **Honor the cap script's exit code.** Even if you're confident, never
  bypass `check_cap.py`. The cap exists so a misclassification costs at
  most $cap.
- **Never write to the user's `settings.json`.** Configuration changes
  go through `/rlm-auto:config`.
- **Don't grade the decision.** That is the evaluator's job. Just route
  and write the outcome.

## What this skill does NOT do

- It does not run the planner if the user has already typed `/rlm:rlm`
  directly. In that case, defer to the base rlm skill.
- It does not collect telemetry or send anything off the machine beyond
  what already flows to the API via the normal Claude Code request.
- It does not retry on RLM failure. If the RLM run fails or returns
  `ok: false`, fall back to a normal Read/Grep flow and write that
  outcome to the log so the evaluator can mark it.

## Required dependency

This skill calls `/rlm:rlm-plan` and `/rlm:rlm`. If those commands are
not registered, the rlm plugin is not installed. Tell the user to
install it (`claude plugin install rlm`) and abort the auto-routing - fall back to a normal direct flow for the current turn.
