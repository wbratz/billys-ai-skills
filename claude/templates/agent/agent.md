---
name: My Agent Name
description: One sentence describing this agent's role and when to spawn it.
version: 1.0.0
author: your-github-handle
category: dev-tools
tags: [tag1, tag2]
# tools: List of tools this agent needs access to.
tools:
  - Read
  - Grep
  - Glob
---

# My Agent Name

<!-- Replace with your agent's system prompt.
     Agents are spawned via the Agent tool with a task-specific prompt.
     Define here:
       - The agent's specialty / domain
       - What it reads and produces
       - How it should communicate its findings back
       - Tools it is allowed to use
       - What it should never do
-->

## Role

Describe the agent's specialty in 2-3 sentences.

## Inputs

What context or arguments does the spawning call need to pass?

## Outputs

What does the agent return in its final message?

## Behavior guidelines

- Guideline one.
- Guideline two.

## Tools

List and justify each tool the agent uses.

## Example invocation

```js
Agent({
  subagent_type: "my-agent-name",
  description: "Short task description",
  prompt: "Detailed prompt here including all context the agent needs..."
})
```
