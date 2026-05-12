"""PDF loader. Extracts per-page text. Optional per-page render for VLM subqueries.

Requires `pypdf` for text extraction. If `pypdf` is not installed, returns a single
context item with an error note so the controller can decide how to proceed.

For --render-pages, requires `pdf2image` + `pillow` (and poppler on PATH).
"""

from __future__ import annotations

from pathlib import Path


def load(path: Path, max_bytes: int | None = None, render_pages: bool = False) -> list[dict]:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        return [{
            "path": str(path),
            "content": f"[pypdf not installed: {exc}. Install: pip install pypdf]",
            "kind": "text",
            "meta": {"error": "pypdf_missing"},
        }]

    reader = PdfReader(str(path))
    items = []
    total = 0
    cap = max_bytes or 5_000_000

    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            text = f"[page {i+1} extraction failed: {exc}]"
        if total + len(text) > cap:
            items.append({
                "path": f"{path}#truncated",
                "content": f"[truncated at page {i+1}, cap={cap} bytes]",
                "kind": "text",
                "meta": {"truncated": True},
            })
            break
        items.append({
            "path": f"{path}#page-{i+1}",
            "content": text,
            "kind": "text",
            "meta": {"page": i + 1, "total_pages": len(reader.pages)},
        })
        total += len(text)

    if render_pages:
        items.extend(_render_pages(path, len(reader.pages)))

    return items


def _render_pages(path: Path, page_count: int) -> list[dict]:
    try:
        from pdf2image import convert_from_path
    except Exception as exc:
        return [{
            "path": str(path),
            "content": f"[pdf2image not installed: {exc}. Skipping page render.]",
            "kind": "text",
            "meta": {"error": "pdf2image_missing"},
        }]
    out_dir = path.parent / f".rlm/render/{path.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)
    images = convert_from_path(str(path))
    out = []
    for i, img in enumerate(images):
        img_path = out_dir / f"page-{i+1}.png"
        img.save(img_path, "PNG")
        out.append({
            "path": f"{path}#page-{i+1}#image",
            "content": "",
            "kind": "image",
            "meta": {"page": i + 1, "image_path": str(img_path)},
        })
    return out
