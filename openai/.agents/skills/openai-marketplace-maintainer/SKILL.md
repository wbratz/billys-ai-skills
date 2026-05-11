---
name: openai-marketplace-maintainer
description: Use when adding, reviewing, or fixing Codex skills, plugins, custom subagents, marketplace entries, or registry metadata under this OpenAI marketplace folder.
---

# OpenAI Marketplace Maintainer

Use this skill when the user asks to create, update, review, or publish Codex artifacts in this folder.

## Workflow

1. Read `AGENTS.md` in this folder first.
2. Identify the artifact type:
   - standalone skill under `skills/`
   - plugin under `plugins/`
   - custom subagent template or active agent
   - marketplace metadata under `.agents/plugins/marketplace.json`
   - registry metadata under `registry/`
3. Start from the matching template in `templates/`.
4. Keep names kebab-case for folders and plugin names.
5. Keep skill names concise and descriptions trigger-focused.
6. Do not create marketplace entries for missing plugin folders.
7. Do not activate custom subagents under `.codex/agents/` unless explicitly asked.
8. Check official OpenAI Codex docs when plugin, skill, agent, or marketplace behavior is uncertain.

## Validation checklist

- `plugins/{name}/.codex-plugin/plugin.json` exists for every plugin marketplace entry.
- Marketplace entry `name` matches plugin manifest `name`.
- Marketplace entry `source.path` is relative to this folder and points to `./plugins/{name}`.
- Marketplace entry includes `policy.installation`, `policy.authentication`, and `category`.
- Each skill has `SKILL.md` with `name` and `description` frontmatter.
- No secrets, tokens, or machine-local absolute paths are committed.

