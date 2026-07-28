# Contributing

Contributions should make the marketplace easier to trust, install, or operate.
Bug reports and focused improvements are welcome.

## Development setup

Requirements:

- Python 3.11 or newer
- Node.js 22 or newer
- npm

Install the validator dependency:

```bash
npm ci --prefix claude/tools
```

Run the same checks used in CI:

```bash
npm audit --prefix claude/tools --omit=dev
npm run validate --prefix claude/tools
python3 scripts/validate_repository.py
python3 -m unittest discover -s claude/plugins/billys-rlm-auto/tests -p "test_*.py" -v
python3 -m unittest discover -s openai/plugins/rlm-codex/tests -p "test_*.py" -v
python3 -m compileall -q claude/plugins openai/plugins
```

## Adding or changing a plugin

Keep each client’s marketplace contract intact:

- Claude Code plugins live in `claude/plugins/` and are registered in
  `claude/.claude-plugin/marketplace.json`.
- Codex plugins live in `openai/plugins/` and are registered in
  `openai/.agents/plugins/marketplace.json`.
- Keep marketplace and plugin manifest names and versions aligned.
- Document setup, credentials, cost controls, and generated-code risks.
- Add tests for behavior changes.

Never commit credentials, private corpora, customer data, or generated RLM
artifacts containing sensitive source material.
