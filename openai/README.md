# OpenAI Codex Marketplace

This directory is the Codex marketplace root for Billy's AI Skills.

## Install

From the repository root:

```bash
codex plugin marketplace add ./openai
```

From this directory:

```bash
codex plugin marketplace add .
```

Install `rlm-codex` from the added marketplace, then follow the
[RLM Codex guide](docs/rlm-codex.md) for prerequisites, health checks, dry runs,
local models, and live execution.

## Structure

- `.agents/plugins/marketplace.json`: Codex marketplace index
- `plugins/rlm-codex/`: packaged RLM plugin and test suite
- `docs/`: operating and marketplace documentation
- `registry/`: human-readable plugin catalog
- `AGENTS.md`: repository instructions for Codex contributors

The repository-wide validation commands are documented in
[`../CONTRIBUTING.md`](../CONTRIBUTING.md).

## Official documentation

- [Codex plugins](https://developers.openai.com/codex/plugins)
- [Build Codex plugins](https://developers.openai.com/codex/plugins/build)
- [AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [Codex skills](https://developers.openai.com/codex/skills)
- [Codex custom agents](https://developers.openai.com/codex/subagents)
