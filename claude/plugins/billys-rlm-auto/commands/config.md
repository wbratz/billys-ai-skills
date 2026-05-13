---
name: config
description: Inspect or change rlm-auto thresholds (min_size_bytes, min_file_count, auto_approve_cap_usd, keyword lists, kill switch). Writes to ~/.rlm/auto-config.json. Never modifies the user's settings.json.
argument-hint: [show | set <key> <value> | reset]
---

# /rlm-auto:config

Manage the user-level config that overrides this plugin's defaults.

## Usage

```
/rlm-auto:config show
/rlm-auto:config set min_size_bytes 102400
/rlm-auto:config set auto_approve_cap_usd 0.25
/rlm-auto:config set enabled false           # kill switch
/rlm-auto:config reset                       # revert to defaults
```

## Workflow

1. Show the merged config (defaults + user overrides). Default location:
   `~/.rlm/auto-config.json`.
2. For `set`, validate the key is in the allowlist:
   - `enabled` (bool)
   - `min_size_bytes` (int >= 0)
   - `min_file_count` (int >= 0)
   - `auto_approve_cap_usd` (float >= 0)
   - `kw_positive` (list[str])
   - `kw_negative` (list[str])
   - `log_full_prompts` (bool)
   - `show_footer` (bool)
3. Read the existing user file (create the dir if missing), merge, write back.
4. Confirm the new value back to the user and remind them to restart Claude
   Code if the hook is currently loaded.

Never edit `${CLAUDE_PLUGIN_ROOT}/config/defaults.json` from this command.
Defaults are for the plugin maintainer to bump; users override via
`~/.rlm/auto-config.json`.

## Recommended tuning workflow

If `/rlm-auto:status` shows >5 false positives at small sizes, raise
`min_size_bytes` to 100 KB. If it shows false negatives where the direct
path read >200 KB, drop `min_size_bytes` to 30 KB and watch the next 20
decisions.
