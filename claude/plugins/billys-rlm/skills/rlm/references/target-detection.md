# Target Detection

How the planner classifies an input target before recommending a mode.

## Detection order

1. **URL?** Starts with `http://` or `https://` → `url`.
2. **Path exists?** Use stat:
   - Regular file → check extension
   - Directory → `dir`
   - Glob pattern (contains `*`, `?`, `[`) → expand, treat as `multi-file`
3. **Stdin or inline text?** → `text`

## File extension → type

| Extensions | Type |
|---|---|
| `.pdf` | `pdf` |
| `.txt`, `.md`, `.rst`, `.org` | `text` |
| `.docx`, `.doc`, `.rtf`, `.odt` | `document` (warn: requires extraction lib) |
| `.log`, `.jsonl`, `.ndjson` | `log` |
| `.csv`, `.tsv`, `.parquet` | `tabular` |
| `.ipynb` | `notebook` |
| `.py`, `.js`, `.ts`, `.go`, `.rs`, `.java`, `.c`, `.cpp`, ... | `code` |
| `.html`, `.htm`, `.xml` | `markup` |
| other text | `text` (best-effort) |
| binary, unknown | `unknown` (warn) |

## Size buckets

| Bytes | Bucket | Suggested mode |
|---|---|---|
| <50KB | tiny | `min` |
| 50KB - 2MB | medium | `default` |
| 2MB - 50MB | large | `default` (with chunking warning) |
| >50MB | huge | `max` (with budget gate) |

For directories, sum text-extractable sizes only (skip binaries, node_modules, .git, etc.).

## File-count buckets (directories / globs)

| Files | Suggested mode |
|---|---|
| 1-5 | `min` |
| 6-50 | `default` |
| 51-500 | `default` |
| >500 | `max` (with budget gate) |

If both size and count point to different modes, pick the higher one.

## Prompt heuristics that bump to `max`

If the user's question contains these patterns, recommend `max` regardless of size:

- "compare across"
- "audit", "review every"
- "trace dependencies"
- "find all places where"
- "exhaustively"
- "for each X, identify Y" (loop language)

## Token estimation

Rough: `tokens ≈ bytes / 4` for English prose, `bytes / 3.5` for code, `bytes / 5` for non-Latin scripts.

The planner prints both raw bytes and estimated tokens.

## Output shape

```json
{
  "target_type": "dir",
  "size_bytes": 184320,
  "file_count": 47,
  "est_tokens": 46080,
  "recommended_mode": "default",
  "reasons": ["medium-size directory", "47 files"],
  "warnings": []
}
```
