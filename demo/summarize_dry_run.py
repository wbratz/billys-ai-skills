#!/usr/bin/env python3
"""Render the runner's dry-run JSON as a compact terminal summary."""

from __future__ import annotations

import json
import sys

payload = json.load(sys.stdin)
if not payload.get("ok"):
    raise SystemExit("RLM dry run failed")

context = payload["context_summary"]
fanout = payload["fanout_plan"]

print(f"✓ {context['file_count']} source files collected")
print(f"✓ {context['chunk_count']} context chunks prepared")
print(
    f"✓ {fanout['estimated_batches']} batches, "
    f"up to {fanout['max_concurrent_recursive_subcalls']} recursive subcalls"
)
print("✓ dry run complete, no provider credentials used")
