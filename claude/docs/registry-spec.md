# Registry Specification

`registry/index.yaml` is the canonical source of truth for all marketplace items.

## Top-level structure

```yaml
skills:   [ ...RegistryEntry ]
agents:   [ ...RegistryEntry ]
plugins:  [ ...RegistryEntry ]
```

## RegistryEntry fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes | Globally unique. Format: `namespace/slug`. Slug is lowercase kebab-case. |
| `type` | enum | Yes | `skill` \| `agent` \| `plugin` |
| `name` | string | Yes | Human-readable name (title case). |
| `description` | string | Yes | One sentence, ≤ 140 chars. |
| `category` | string | Yes | Must match an `id` in `registry/categories.yaml`. |
| `author` | string | Yes | GitHub handle of the primary author. |
| `version` | string | Yes | Semver (`1.0.0`). |
| `path` | string | Yes | Relative path to the definition file from repo root. |
| `tags` | string[] | No | Lowercase keywords for search. Max 8. |
| `deprecated` | boolean | No | Set `true` when superseded; do not delete the entry. |
| `replaces` | string | No | ID of the entry this one supersedes. |
| `min_claude_version` | string | No | Minimum Claude Code version required (semver). |

## Namespace ownership

A namespace prefix (e.g., `billyz/`, `acme/`) is claimed by the first author to merge under it. Subsequent entries under that namespace require maintainer approval from the namespace owner.

## Versioning policy

- Increment **patch** (`1.0.x`) for bug fixes and wording improvements.
- Increment **minor** (`1.x.0`) for new capabilities that don't break existing behavior.
- Increment **major** (`x.0.0`) for breaking changes (renamed triggers, removed steps, changed outputs).

## Deprecation

Never delete a registry entry — set `deprecated: true` and optionally `replaces`. This preserves install history and allows graceful migration messaging.
