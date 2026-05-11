# Codex Plugins

Put shareable Codex plugins here.

Each plugin should use this shape:

```text
plugins/{plugin-name}/
  .codex-plugin/
    plugin.json
  skills/
  .mcp.json
  .app.json
  hooks/
    hooks.json
  assets/
```

Only `plugin.json` belongs inside `.codex-plugin/`. Keep all other plugin components at the plugin root.

Add installable plugins to `../.agents/plugins/marketplace.json`.

