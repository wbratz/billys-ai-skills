# OpenAI Codex Skills, Agents, and Plugins Marketplace

## What this folder is

This folder is a Codex-oriented marketplace/workbench for reusable OpenAI agent capabilities: Codex skills, Codex plugins, custom Codex subagents, MCP tool bundles, and supporting docs.

The Claude Code equivalent in this repo is `claude/CLAUDE.md`. For Codex, the project instruction file is `AGENTS.md`.

## Repo layout

```text
.agents/
  plugins/marketplace.json        Codex local marketplace index.
  skills/                         Codex maintenance skills for this marketplace repo.
agents/                           Shared custom Codex subagent definitions and docs.
plugins/                          One directory per Codex plugin package.
skills/                           Standalone shareable Codex skills.
registry/                         Optional human-readable index and taxonomy.
templates/                        Starter scaffolds for skills, plugins, and agents.
docs/                             Authoring guides and notes.
tools/                            Validation and publishing scripts.
```

## Codex conventions

- Codex project instructions live in `AGENTS.md`.
- A Codex plugin has `.codex-plugin/plugin.json` at the plugin root.
- Plugin components stay at the plugin root, not inside `.codex-plugin/`.
- Plugin components can include `skills/`, `.mcp.json`, `.app.json`, `hooks/hooks.json`, and `assets/`.
- A Codex marketplace root contains `.agents/plugins/marketplace.json`.
- Marketplace entries point to plugin folders with paths relative to this `openai/` folder, usually `./plugins/{plugin-name}`.
- A Codex skill is a directory containing `SKILL.md` with frontmatter `name` and `description`.
- Shareable standalone skills live in `skills/`; repo-maintenance skills that Codex should auto-discover live in `.agents/skills/`.
- Project-scoped custom Codex agents are TOML files under `.codex/agents/` when active. Keep reusable templates in `templates/agent/` until they are ready to install.

## Marketplace workflow

- Add a plugin under `plugins/{plugin-name}/`.
- Ensure `plugins/{plugin-name}/.codex-plugin/plugin.json` exists and has a stable kebab-case `name`.
- Add or update a matching entry in `.agents/plugins/marketplace.json`.
- Keep `policy.installation`, `policy.authentication`, and `category` present on every marketplace entry.
- Use `AVAILABLE` for normal shareable plugins.
- Use `NOT_AVAILABLE` for examples or placeholders that should not be installed.
- Do not publish secrets, API keys, or machine-local absolute paths in plugin manifests.

## Adding a new standalone skill

1. Copy `templates/skill/` to `skills/{namespace}-{slug}/`.
2. Fill in `SKILL.md`.
3. Add a registry entry if this skill should be indexed.
4. Keep descriptions concise and front-load trigger words. Codex may shorten long skill descriptions in the initial skill list.

## Adding a new plugin

1. Copy `templates/plugin/` to `plugins/{plugin-name}/`.
2. Rename placeholders in `.codex-plugin/plugin.json`.
3. Add real skills, MCP servers, hooks, apps, and assets only as needed.
4. Add the plugin to `.agents/plugins/marketplace.json`.
5. Test from this folder with:

```bash
codex plugin marketplace add .
```

or from the parent repo with:

```bash
codex plugin marketplace add ./openai
```

## Adding a custom Codex subagent

1. Start from `templates/agent/agent.toml`.
2. Save active project agents under `.codex/agents/{agent-name}.toml`.
3. Keep reusable unpublished templates under `templates/agent/`.
4. Keep custom agents narrow. They should have a clear job, tool surface, and stopping condition.

## What Codex should do here

- Help authors scaffold new Codex skills, plugins, and custom subagents from templates.
- Keep marketplace entries consistent with actual plugin folders.
- Prefer official OpenAI Codex docs when behavior is unclear or may have changed.
- Never add a marketplace entry for a plugin unless the plugin folder and `.codex-plugin/plugin.json` exist.
- Never place template agents directly under `.codex/agents/` unless the user asks to activate them.
- Keep this folder platform-specific to OpenAI/Codex. Claude Code artifacts belong under `../claude/`.

## Registry entry shape

```yaml
- id: namespace/slug
  type: skill
  name: Human Name
  description: One sentence.
  category: dev-tools
  author: github-handle
  version: 1.0.0
  path: skills/namespace-slug/SKILL.md
  tags: [codex, automation]
```

For plugins, use `type: plugin` and point `path` to `plugins/{plugin-name}/.codex-plugin/plugin.json`.

