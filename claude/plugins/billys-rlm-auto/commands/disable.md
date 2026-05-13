---
name: disable
description: Disable passive RLM routing for the rest of this session, or persistently. The hook still runs but exits immediately. Re-enable with /rlm-auto:config set enabled true.
argument-hint: [--persistent]
---

# /rlm-auto:disable

Turn off passive routing without uninstalling the plugin.

## Usage

```
/rlm-auto:disable                # session-only: set RLM_AUTO_DISABLE=1
/rlm-auto:disable --persistent   # write enabled=false to ~/.rlm/auto-config.json
```

## Workflow

1. **Session-only:** export the kill-switch env var:

   ```bash
   $env:RLM_AUTO_DISABLE = "1"        # PowerShell
   export RLM_AUTO_DISABLE=1          # bash
   ```

   Tell the user this only persists until they restart Claude Code.

2. **Persistent:** delegate to `/rlm-auto:config set enabled false`.

After disabling, the hook still loads but `load_config()` returns
`enabled=false` and the hook exits without injecting a reminder. The
decision log is untouched.

To re-enable: `/rlm-auto:config set enabled true` (clears the persistent
flag) and unset `RLM_AUTO_DISABLE`.
