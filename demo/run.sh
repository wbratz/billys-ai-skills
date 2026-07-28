#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runner="$repository_root/openai/plugins/rlm-codex/skills/rlm/scripts/rlm_run.py"
corpus="$repository_root/examples/product-launch"

echo '$ codex'
echo '> Use RLM over examples/product-launch.'
echo '> What changed between the PRD and implementation, and what launch risks remain?'
echo
echo 'RLM dry run'

python3 "$runner" \
  --prompt "What changed between the PRD and implementation, why did it change, and what launch risks remain?" \
  --context "$corpus" \
  --chunk-size 700 \
  --chunk-overlap 100 \
  --batch-size 4 \
  --max-concurrent-subcalls 4 \
  --dry-run \
  --json | python3 "$repository_root/demo/summarize_dry_run.py"

echo
echo 'Recorded example synthesis'
echo
sed -n '3,$p' "$repository_root/demo/expected-synthesis.md"
echo
echo 'The dry run above executes locally without credentials.'
echo 'The synthesis is a checked-in example of the live workflow and is not regenerated during this demo.'
