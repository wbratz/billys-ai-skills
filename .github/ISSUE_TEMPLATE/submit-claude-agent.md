---
name: Submit a Claude Agent
about: Propose a new Claude Code agent definition for the marketplace
title: "[Agent] Your Agent Name"
labels: submission, agent
assignees: ''
---

## Agent name

## Namespace/slug (registry ID)

## Category

## Description (<= 140 chars)

## What is this agent's specialty?

## Tools it requires

<!-- List each tool and why it is needed. -->

## Example spawning prompt

```js
Agent({
  subagent_type: "...",
  description: "...",
  prompt: "..."
})
```

## PR checklist

- [ ] Copied from `claude/templates/agent/`
- [ ] `agent.md` frontmatter fully filled in
- [ ] Entry added to `claude/registry/index.yaml`
- [ ] `cd claude/tools && npm install && node validate.js` passes locally
- [ ] Tested - include a brief description of the test case
