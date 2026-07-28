# RLM Use Cases

The 8 input shapes this plugin supports, with recommended config and loader for each.

## 1. Single large document (PDF / Word / MD / TXT)

**When:** One document too big to comfortably read end-to-end. Contracts, research papers, long specs, books.

**Loader:** `loaders/load_file.py` (text), `loaders/load_pdf.py` (PDF with per-page text + optional render).

**Recommended:** `mode=default`. The controller chunks by page or by section, batches Haiku extraction, synthesizes.

**Sample prompts:**
- "Summarize section by section, then identify contradictions."
- "Extract all numeric claims with page citations."
- "What does this paper say about <topic>? Cite passages."

## 2. Directory / codebase

**When:** Multi-file analysis where files reference each other. Codebase walkthroughs, architecture audits, dependency mapping.

**Loader:** `loaders/load_dir.py` (respects `.gitignore`, configurable extensions, max-bytes cap).

**Recommended:** `mode=default` for <2MB, `mode=max` for monorepos.

**Sample prompts:**
- "What does this codebase do?"
- "List every place where authentication is checked."
- "Map module dependencies and flag circular imports."

## 3. Logs and transcripts

**When:** Time-series text. Server logs, chat transcripts, meeting recordings (text), incident timelines.

**Loader:** `loaders/load_logs.py` (line-oriented, optional timestamp parsing, JSONL aware).

**Recommended:** `mode=min` for single log <50KB, `mode=default` for incident corpora.

**Sample prompts:**
- "What error pattern caused the outage starting at 14:32?"
- "Summarize this meeting and extract action items."
- "Group these 10k log lines by failure mode."

## 4. Multi-doc corpus QA

**When:** Question that requires reading multiple docs together. Research, legal discovery, knowledge-base QA.

**Loader:** combo of `load_dir.py` + `load_pdf.py`.

**Recommended:** `mode=default` or `mode=max` depending on corpus size.

**Sample prompts:**
- "What do these 30 papers collectively say about transformer scaling?"
- "Find all clauses across these contracts that mention indemnification."

## 5. Website / URL

**When:** Public web content. Single page or bounded crawl.

**Loader:** `loaders/load_url.py` (fetches, strips boilerplate, optional depth=1 crawl).

**Recommended:** `mode=min` for a single page, `mode=default` for a small crawl. Crawling is bounded by max-pages (default 20).

**Sample prompts:**
- "Read this blog post and extract the author's main argument."
- "Crawl this docs site and answer: how do I configure X?"

## 6. Structured extraction with citations

**When:** Contracts, medical charts, legal filings, regulatory docs. Output must be auditable.

**Loader:** `load_pdf.py` with `--preserve-spans` (keeps page/paragraph offsets in chunk metadata).

**Recommended:** `mode=default`. The controller is prompted to emit JSON with `{value, source_page, source_span}` per extracted field.

**Sample prompts:**
- "Extract all parties, dates, and dollar amounts from this contract. Cite the page for each."
- "List medications, doses, and frequencies from this discharge summary."

## 7. Notebooks / JSONL / tabular dumps

**When:** Semi-structured data dumps. Jupyter notebooks, JSONL records, CSV/Parquet exports.

**Loader:** `loaders/load_file.py` (autodetects JSONL/CSV by extension, samples large files).

**Recommended:** `mode=default`. The controller can write Python to subset/filter in the REPL before fanning out.

**Sample prompts:**
- "Profile this JSONL: types, distributions, anomalies."
- "Read this notebook and write a plain-English summary of what it does."

## 8. Multimodal documents (PDF pages as images)

**When:** PDFs with figures, charts, diagrams, or scanned content where OCR alone loses information.

**Loader:** `load_pdf.py --render-pages` (renders each page as PNG; chunks become `{type: "image", path: ...}` parts).

**Recommended:** `mode=default`. `llm_query` is routed to Haiku 4.5 which has vision; the controller fans out per-page image queries.

**Sample prompts:**
- "What chart trends are shown in this report? Which pages?"
- "Read this scanned contract (OCR low quality) - extract parties and dates."

## Cost & latency expectations (rough)

| Mode + use case | Typical cost | Wall-clock |
|---|---|---|
| min, single doc <50KB | $0.02-0.10 | 10-30s |
| default, corpus QA ~500KB | $0.40-1.20 | 1-3 min |
| default, multi-PDF research | $1-3 | 2-5 min |
| max, monorepo audit | $3-10 | 5-15 min |

Numbers assume default mode routing (Opus root + Sonnet depth-1 + Haiku fanout) and typical fanout widths. Concrete cost printed in the plan step before execution.
