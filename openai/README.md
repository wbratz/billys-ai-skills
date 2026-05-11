# Billy's OpenAI Skills and Plugins

This folder is a Codex marketplace root and authoring workspace for OpenAI/Codex skills, plugins, custom subagents, and MCP tool bundles.

## Install this marketplace locally

From `C:\dev\billys-ai-skills`:

```bash
codex plugin marketplace add ./openai
```

From inside this folder:

```bash
codex plugin marketplace add .
```

Codex marketplace metadata lives at:

```text
.agents/plugins/marketplace.json
```

## Main folders

- `AGENTS.md`: Codex project instructions. This is the Codex equivalent of `CLAUDE.md`.
- `.agents/plugins/marketplace.json`: local marketplace index for Codex plugins.
- `.agents/skills/`: repo-maintenance skills that Codex can discover while working here.
- `skills/`: standalone shareable Codex skills.
- `plugins/`: packaged Codex plugins.
- `agents/`: shared docs or published custom agent definitions.
- `templates/`: starter scaffolds.
- `registry/`: optional human-readable index and categories.
- `docs/`: authoring docs.
- `tools/`: future validation/publishing scripts.

## Official docs

- Codex plugins: https://developers.openai.com/codex/plugins
- Build Codex plugins: https://developers.openai.com/codex/plugins/build
- Codex AGENTS.md: https://developers.openai.com/codex/guides/agents-md
- Codex skills: https://developers.openai.com/codex/skills
- Codex custom subagents: https://developers.openai.com/codex/subagents

