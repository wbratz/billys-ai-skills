"""URL loader. Single page by default; bounded crawl with --max-pages.

Strips boilerplate via a simple HTML-to-text fallback. Uses `httpx` + `selectolax`
when available, falls back to stdlib `urllib` + `html.parser`.
"""

from __future__ import annotations

import html.parser
import re
import urllib.parse
import urllib.request


class _Stripper(html.parser.HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip_depth > 0:
            self.skip_depth -= 1

    def handle_data(self, data):
        if self.skip_depth == 0:
            self.parts.append(data)


def _fetch(url: str, timeout: float = 15.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "billys-rlm/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ctype = resp.headers.get("Content-Type", "")
        raw = resp.read()
        enc = "utf-8"
        m = re.search(r"charset=([\w-]+)", ctype)
        if m:
            enc = m.group(1)
        return raw.decode(enc, errors="replace")


def _strip(html_text: str) -> str:
    s = _Stripper()
    s.feed(html_text)
    text = "".join(s.parts)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def load(url: str, max_bytes: int | None = None, max_pages: int = 1) -> list[dict]:
    items = []
    seen = set()
    queue = [url]
    cap = max_bytes or 5_000_000
    total = 0

    while queue and len(items) < max_pages:
        u = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        try:
            html_text = _fetch(u)
        except Exception as exc:
            items.append({
                "path": u,
                "content": f"[fetch failed: {exc}]",
                "kind": "text",
                "meta": {"error": str(exc)},
            })
            continue
        text = _strip(html_text)
        if total + len(text) > cap:
            text = text[: cap - total]
        items.append({
            "path": u,
            "content": text,
            "kind": "text",
            "meta": {"url": u, "byte_len": len(text)},
        })
        total += len(text)
        if max_pages > 1:
            for link in _extract_links(html_text, u):
                if link not in seen and len(items) + len(queue) < max_pages:
                    queue.append(link)
        if total >= cap:
            break
    return items


def _extract_links(html_text: str, base: str) -> list[str]:
    base_parsed = urllib.parse.urlparse(base)
    links = []
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html_text):
        href = m.group(1)
        if href.startswith(("#", "javascript:", "mailto:")):
            continue
        absolute = urllib.parse.urljoin(base, href)
        parsed = urllib.parse.urlparse(absolute)
        if parsed.netloc != base_parsed.netloc:
            continue
        links.append(absolute.split("#")[0])
    return links
