---
name: My Plugin Name
description: One sentence describing this plugin (MCP server, tool bundle, etc.).
version: 1.0.0
author: your-github-handle
category: integrations
tags: [tag1, tag2]
# plugin_type: mcp-server | tool-bundle | hook-bundle
plugin_type: mcp-server
---

# My Plugin Name

<!-- Replace with your plugin's documentation.
     For MCP servers: describe the tools it exposes, auth requirements, and install steps.
     For tool bundles: list each tool and its purpose.
     For hook bundles: list each hook event and what it does.
-->

## What this plugin provides

Describe what capabilities this plugin adds to Claude Code.

## Install

```bash
# Add to .claude/settings.json mcpServers block:
{
  "my-plugin": {
    "command": "npx",
    "args": ["-y", "@your-org/my-plugin-mcp"]
  }
}
```

## Configuration

| Variable | Required | Description |
|---|---|---|
| `MY_API_KEY` | Yes | API key for the service |

## Tools / capabilities exposed

| Tool name | Description |
|---|---|
| `tool_one` | Does X |
| `tool_two` | Does Y |

## Notes

Any auth flows, rate limits, or caveats.
