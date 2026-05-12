"""Generic single-file loader. Handles text, code, markdown, JSONL (samples large files)."""

from __future__ import annotations

import json
from pathlib import Path


def load(path: Path, max_bytes: int | None = None) -> list[dict]:
    suf = path.suffix.lower()
    if suf in {".jsonl", ".ndjson"}:
        return _load_jsonl(path, max_bytes)
    return _load_text(path, max_bytes)


def _load_text(path: Path, max_bytes: int | None) -> list[dict]:
    data = path.read_text(errors="replace")
    if max_bytes and len(data) > max_bytes:
        data = data[:max_bytes]
    return [{
        "path": str(path),
        "content": data,
        "kind": "text",
        "meta": {"size_bytes": path.stat().st_size, "truncated": bool(max_bytes and len(data) >= max_bytes)},
    }]


def _load_jsonl(path: Path, max_bytes: int | None) -> list[dict]:
    items = []
    total = 0
    cap = max_bytes or 2_000_000
    with path.open("r", errors="replace") as f:
        for i, line in enumerate(f):
            if total + len(line) > cap:
                items.append({
                    "path": f"{path}#truncated",
                    "content": f"[truncated after {i} records, cap={cap} bytes]",
                    "kind": "text",
                    "meta": {"truncated": True},
                })
                break
            try:
                obj = json.loads(line)
                items.append({
                    "path": f"{path}#{i}",
                    "content": json.dumps(obj, indent=2),
                    "kind": "structured",
                    "meta": {"record_index": i},
                })
            except json.JSONDecodeError:
                items.append({
                    "path": f"{path}#{i}",
                    "content": line.rstrip("\n"),
                    "kind": "text",
                    "meta": {"record_index": i, "parse_failed": True},
                })
            total += len(line)
    return items
