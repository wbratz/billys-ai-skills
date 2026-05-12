"""Directory loader. Respects ignore rules, caps total bytes, prefers text-like files."""

from __future__ import annotations

import os
from pathlib import Path

IGNORE_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache",
                "dist", "build", "target", ".next", ".nuxt", ".idea", ".vscode",
                ".rlm"}

BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pdf", ".zip",
                ".tar", ".gz", ".bz2", ".xz", ".7z", ".exe", ".dll", ".so", ".dylib",
                ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".mp3", ".wav"}


def load(root: Path, max_bytes: int | None = None) -> list[dict]:
    cap = max_bytes or 5_000_000
    items = []
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in BINARY_EXTS:
                continue
            try:
                sz = p.stat().st_size
            except OSError:
                continue
            if sz > 1_000_000:
                continue
            if total + sz > cap:
                items.append({
                    "path": f"{root}#truncated",
                    "content": f"[directory load truncated at {cap} bytes; {len(items)} files included]",
                    "kind": "text",
                    "meta": {"truncated": True},
                })
                return items
            try:
                content = p.read_text(errors="replace")
            except Exception:
                continue
            items.append({
                "path": str(p.relative_to(root)),
                "content": content,
                "kind": "code" if p.suffix.lower() in {".py", ".js", ".ts", ".go", ".rs"} else "text",
                "meta": {"size_bytes": sz, "abs_path": str(p)},
            })
            total += sz
    return items
