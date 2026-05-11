# Codex Marketplace Notes

Codex supports plugin marketplaces. A marketplace can be a local marketplace root or a Git-backed source added with:

```bash
codex plugin marketplace add ./openai
```

The marketplace root for this folder is `openai/`. Its marketplace index is:

```text
openai/.agents/plugins/marketplace.json
```

Marketplace entries should point at plugin folders relative to `openai/`:

```json
{
  "name": "example-plugin",
  "source": {
    "source": "local",
    "path": "./plugins/example-plugin"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Productivity"
}
```

Important docs:

- https://developers.openai.com/codex/plugins
- https://developers.openai.com/codex/plugins/build
- https://developers.openai.com/codex/guides/agents-md
- https://developers.openai.com/codex/skills
- https://developers.openai.com/codex/subagents

