---
name: Submit a Claude Plugin
about: Propose a new Claude Code plugin (MCP server, tool bundle, hook bundle) for the marketplace
title: "[Plugin] Your Plugin Name"
labels: submission, plugin
assignees: ''
---

## Plugin name

## Namespace/slug (registry ID)

## Plugin type

<!-- mcp-server | tool-bundle | hook-bundle -->

## Category

## Description (<= 140 chars)

## What tools/capabilities does it expose?

## Install snippet

```json
{
  "mcpServers": {
    "your-plugin": {}
  }
}
```

## Auth/config requirements

## PR checklist

- [ ] Copied from `claude/templates/plugin/`
- [ ] `plugin.md` frontmatter fully filled in
- [ ] Entry added to `claude/registry/index.yaml`
- [ ] `cd claude/tools && npm install && node validate.js` passes locally
- [ ] Install instructions verified
