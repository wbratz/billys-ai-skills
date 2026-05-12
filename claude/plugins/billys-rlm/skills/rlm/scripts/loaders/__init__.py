"""Loaders convert a target (file/dir/PDF/URL/log) into a list of context items.

Each loader returns a list of dicts with at minimum:
  - "path": source path or URL
  - "content": text content (or "image" + "image_path" for multimodal)
  - "kind": "text" | "image" | "structured"
  - "meta": optional dict (page numbers, byte offsets, etc.)
"""
