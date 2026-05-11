---
name: Submit a Claude Skill
about: Propose a new Claude Code skill for the marketplace
title: "[Skill] Your Skill Name"
labels: submission, skill
assignees: ''
---

## Skill name

<!-- Human-readable title -->

## Namespace/slug (registry ID)

<!-- e.g., billyz/git-autopilot -->

## Category

<!-- Must match an id in claude/registry/categories.yaml -->

## Description (<= 140 chars)

## What problem does it solve?

<!-- 2-3 sentences on the use case and why it belongs in this marketplace. -->

## Trigger phrases (if any)

<!-- List natural-language phrases that should auto-invoke this skill. -->

## PR checklist

- [ ] Copied from `claude/templates/skill/`
- [ ] `skill.md` frontmatter fully filled in
- [ ] Entry added to `claude/registry/index.yaml`
- [ ] `cd claude/tools && npm install && node validate.js` passes locally
- [ ] Tested in at least one real Claude Code session
