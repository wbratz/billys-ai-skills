# Standalone Codex Skills

Put shareable standalone Codex skills here.

Each skill should use this shape:

```text
skills/{namespace}-{slug}/
  SKILL.md
  references/
  scripts/
  assets/
```

`SKILL.md` must include:

```yaml
---
name: skill-name
description: Trigger-focused description for when Codex should use this skill.
---
```

Use `../templates/skill/` as the starter.

