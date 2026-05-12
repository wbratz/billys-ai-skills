# Claude Skills & Agent Marketplace

## What this repo is

A community marketplace for Claude Code **skills**, **agents**, and **plugins** — reusable, installable capabilities that extend what Claude Code can do. Authors publish here; users discover and install from here.

## Repo layout

```
.claude-plugin/  Marketplace manifest (marketplace.json) — registers this repo as a Claude Code marketplace.
skills/          One directory per skill. Each contains skill.md + README.md.
agents/          One directory per agent definition. Each contains agent.md + README.md.
plugins/         One directory per plugin (MCP servers, tool bundles). Contains plugin.md + README.md.
registry/        The canonical index (index.yaml) and category taxonomy (categories.yaml).
templates/       Starter scaffolds for new skill/agent/plugin submissions.
docs/            Authoring guides, registry spec, install instructions.
tools/           CLI scripts: validate, publish, lint registry entries.
.github/         Issue templates (submit-skill, submit-agent) and CI workflows.
```

## Installing the marketplace in Claude Code

```bash
claude marketplace add <path-or-url-to-this-repo>
claude plugin install <plugin-name>     # e.g. `rlm`
```

`.claude-plugin/marketplace.json` lists every available plugin. Every new plugin should be added there in the same PR as its registry entry.

## Key conventions

- Every skill/agent/plugin lives in its own subdirectory named `{namespace}-{slug}` (e.g., `skills/commit-commands-commit/`).
- The primary definition file is always named `skill.md`, `agent.md`, or `plugin.md`.
- `registry/index.yaml` is the single source of truth for discovery — every merged item must have an entry there.
- Namespaces are owned: once `foo:` is registered, only that author may publish under it.

## Working in this repo

- **Adding a new skill**: copy `templates/skill/`, fill in the template, then add an entry to `registry/index.yaml`.
- **Validation**: run `node tools/validate.js` before submitting a PR — CI will block merges that fail.
- **Categories**: defined in `registry/categories.yaml`. Propose new ones via issue before using them.

## What Claude should do here

- Help authors scaffold new skills/agents from templates.
- Validate that `registry/index.yaml` entries are consistent with the actual files in `skills/`, `agents/`, `plugins/`.
- Suggest categories and metadata improvements.
- Never modify `registry/index.yaml` for a submission without also verifying the corresponding definition file exists.
- When asked to "add a skill", always start from the template, not from scratch.

## Registry entry shape (quick reference)

```yaml
- id: namespace/slug
  type: skill          # skill | agent | plugin
  name: Human Name
  description: One sentence.
  category: dev-tools  # must exist in categories.yaml
  author: github-handle
  version: 1.0.0
  path: skills/namespace-slug/skill.md
  tags: [git, automation]
```
