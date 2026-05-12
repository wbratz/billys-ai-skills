"""Log loader. Line-oriented. Detects JSONL vs plain text. Caps total bytes."""

from __future__ import annotations

import json
from pathlib import Path


def load(path: Path, max_bytes: int | None = None) -> list[dict]:
    cap = max_bytes or 5_000_000
    sz = path.stat().st_size
    suf = path.suffix.lower()

    if suf in {".jsonl", ".ndjson"}:
        return _load_jsonl(path, cap)
    return _load_plain(path, cap, sz)


def _load_plain(path: Path, cap: int, sz: int) -> list[dict]:
    if sz <= cap:
        return [{
            "path": str(path),
            "content": path.read_text(errors="replace"),
            "kind": "text",
            "meta": {"size_bytes": sz, "format": "plain-log"},
        }]
    head_cap = cap // 2
    tail_cap = cap - head_cap
    with path.open("rb") as f:
        head = f.read(head_cap).decode(errors="replace")
        f.seek(sz - tail_cap)
        tail = f.read(tail_cap).decode(errors="replace")
    return [
        {
            "path": f"{path}#head",
            "content": head,
            "kind": "text",
            "meta": {"slice": "head", "bytes": head_cap, "of_total": sz},
        },
        {
            "path": f"{path}#tail",
            "content": tail,
            "kind": "text",
            "meta": {"slice": "tail", "bytes": tail_cap, "of_total": sz, "note": "middle skipped"},
        },
    ]


def _load_jsonl(path: Path, cap: int) -> list[dict]:
    items = []
    total = 0
    with path.open("r", errors="replace") as f:
        for i, line in enumerate(f):
            if total + len(line) > cap:
                items.append({
                    "path": f"{path}#truncated",
                    "content": f"[truncated after {i} records]",
                    "kind": "text",
                    "meta": {"truncated": True},
                })
                break
            try:
                obj = json.loads(line)
                items.append({
                    "path": f"{path}#{i}",
                    "content": json.dumps(obj),
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
