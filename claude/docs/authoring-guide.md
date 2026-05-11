# Authoring Guide

How to write and publish a skill, agent, or plugin to this marketplace.

## 1. Choose the right type

| Type | Use when... |
|---|---|
| **Skill** | You want a slash command or trigger phrase that Claude executes inline in the main conversation. |
| **Agent** | You want a specialized sub-agent spawned via the `Agent` tool with its own tools and focus. |
| **Plugin** | You want to expose new tools to Claude via an MCP server or bundle external integrations. |

## 2. Scaffold from a template

```bash
# Copy the right template
cp -r templates/skill/ skills/your-namespace-your-slug/
# or
cp -r templates/agent/ agents/your-namespace-your-slug/
# or
cp -r templates/plugin/ plugins/your-namespace-your-slug/
```

Naming convention: `{github-handle}-{slug}` or `{org}-{slug}`.  
Examples: `billyz-git-autopilot`, `acme-linear-triage`.

## 3. Fill in the definition file

Edit `skill.md` (or `agent.md` / `plugin.md`):

- **Frontmatter**: set all required fields (name, description, version, author, category, tags).
- **Body**: write the skill's instructions as if briefing Claude directly — be specific about steps, inputs, outputs, and edge cases.

## 4. Add a registry entry

Open `registry/index.yaml` and append under the right section:

```yaml
- id: your-namespace/your-slug
  type: skill
  name: Your Skill Name
  description: One sentence.
  category: dev-tools        # must exist in registry/categories.yaml
  author: your-github-handle
  version: 1.0.0
  path: skills/your-namespace-your-slug/skill.md
  tags: [tag1, tag2]
```

## 5. Validate

```bash
node tools/validate.js
```

Fix any errors before opening a PR. CI will run the same check.

## 6. Open a PR

Use the "Submit Skill", "Submit Agent", or "Submit Plugin" issue/PR template. Fill in every section — incomplete submissions will be closed without review.

## Authoring tips

- **Triggers matter**: if your skill has natural trigger phrases ("when the user says X"), list them — they make the skill discoverable without remembering the slash command.
- **Scope tightly**: a skill that does one thing well beats a skill that tries to do five.
- **No hardcoded paths**: write skills that work in any repo, not just yours.
- **Version correctly**: bump the patch version for fixes, minor for new behavior, major for breaking changes.
