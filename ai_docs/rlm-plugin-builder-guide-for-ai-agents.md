# RLM Plugin Builder Guide for AI Agents

Research date: 2026-05-11  
Target reader: AI coding agents that need to build, maintain, or use Recursive Language Model (RLM) plugins for Claude Code and Codex.

This document is written as an operational guide. It assumes the reader can edit files, run commands, inspect a repository, and package local plugin directories. It intentionally separates the RLM runtime invariant from Claude Code and Codex packaging details.

## Source Base

Primary sources inspected:

- RLM paper: https://arxiv.org/abs/2512.24601 and HTML v2 at https://arxiv.org/html/2512.24601v2
- RLM implementation: https://github.com/alexzhang13/rlm, reviewed at commit `03a1774`
- RLM docs in this repository: `README.md`, `docs/architecture.md`, `docs/api/rlm.md`, examples, tests, and `AGENTS.md`
- Claude Code plugin docs: https://code.claude.com/docs/en/plugins and https://code.claude.com/docs/en/plugins-reference
- Codex plugin docs: https://developers.openai.com/codex/plugins and https://developers.openai.com/codex/plugins/build
- Codex extension docs: AGENTS.md, hooks, MCP, skills, and subagents at https://developers.openai.com/codex/
- Community signals: RLM GitHub issues, PRs, and discussions as of 2026-05-11

## Core RLM Contract

An RLM is not a larger prompt. It is a loop around a model, an execution environment, and recursive model calls.

The minimum correct RLM contract is:

1. Store the full task context outside the model prompt as a REPL variable, usually `context`.
2. Give the model a compact system prompt that explains the REPL, available helper functions, and final-answer protocol.
3. Let the model respond with executable code in fenced `repl` blocks.
4. Execute those code blocks in a persistent namespace.
5. Append the execution result, not the full hidden context, back into the model-visible message history.
6. Let executed code call:
   - `llm_query(prompt, model=None)` for one-shot sub-LLM calls.
   - `llm_query_batched(prompts, model=None)` for parallel independent one-shot calls.
   - `rlm_query(prompt, model=None)` for child RLM calls that get their own REPL loop.
   - `rlm_query_batched(prompts, model=None)` for multiple child RLM calls.
7. Stop only when the model emits `FINAL(...)` or calls `FINAL_VAR(...)` on a previously created REPL variable.

The important invariant for plugin builders:

```text
Do not put the whole long context into the Claude Code or Codex conversation.
Package a workflow that runs an RLM runner, MCP tool, or skill, and let that
workflow place large context in an external execution environment.
```

## Paper-Level Model

The RLM paper frames long-context processing as inference-time scaling. The model receives an external environment containing the prompt/context, then writes code to inspect, decompose, and recursively call models over pieces of that context.

Key paper lessons to preserve in plugins:

- RLM is task-agnostic. The root model decides chunking, decomposition, and aggregation strategy.
- Context can exceed model context length because the raw context lives outside the model prompt.
- The REPL is both memory and control plane. It stores intermediate variables, executes deterministic transforms, and launches subcalls.
- Recursive calls are useful only when the subtask itself needs multi-step reasoning. Use `llm_query` for extraction/classification/summarization over a chunk.
- The authors found unoptimized synchronous calls slow. Treat async, batching, caching, and concurrency caps as first-class engineering requirements.
- Final-answer tagging is brittle. The paper notes that models confuse final-answer tags with intermediate reasoning, and Appendix B reports trajectory cleanup for wrong `FINAL` / `FINAL_VAR` usage.
- Model choice matters. Models without enough coding ability or output budget struggle as RLM controllers.
- System prompts should be tuned per model. The paper reports that reusing a prompt written for GPT-5 produced undesirable behavior in Qwen3-Coder and required adjustment.

## Implementation Anatomy

The current Python package is `rlms`, imported as `rlm`. It requires Python `>=3.11` and supports clients for OpenAI-compatible APIs, Anthropic, Azure OpenAI, Gemini, Portkey/OpenRouter/Vercel/vLLM style routing, plus multiple REPL environments.

Important files:

- `rlm/core/rlm.py`: main RLM loop, depth handling, compaction, budgets, timeouts, subcalls.
- `rlm/core/lm_handler.py`: per-completion TCP server that routes model calls.
- `rlm/core/comms_utils.py`: length-prefixed JSON socket protocol.
- `rlm/environments/base_env.py`: environment interfaces and custom tool contract.
- `rlm/environments/local_repl.py`: in-process Python `exec` environment.
- `rlm/environments/ipython_repl.py`: IPython in-process or subprocess kernel environment.
- `rlm/environments/docker_repl.py`, `modal_repl.py`, `prime_repl.py`, `daytona_repl.py`, `e2b_repl.py`: isolated or semi-isolated execution backends.
- `rlm/utils/prompts.py`: default RLM system prompt.
- `rlm/utils/parsing.py`: `repl` block extraction, `FINAL` / `FINAL_VAR` parsing, iteration formatting.
- `rlm/logger/rlm_logger.py`: in-memory and JSONL trajectory logging.

### Main Loop

`RLM.completion(prompt, root_prompt=None)` does this:

```python
if self.depth >= self.max_depth:
    return self._fallback_answer(prompt)

with self._spawn_completion_context(prompt) as (lm_handler, environment):
    message_history = self._setup_prompt(prompt)
    for i in range(self.max_iterations):
        check_timeout()
        maybe_compact_history()
        current_prompt = message_history + [build_user_prompt(...)]
        response = lm_handler.completion(current_prompt)
        code_blocks = find_code_blocks(response)
        for block in code_blocks:
            result = environment.execute_code(block)
        final = final_from_REPL_FINAL_VAR_or_FINAL(response)
        if final is not None:
            return RLMChatCompletion(...)
        message_history.extend(format_iteration(response, code_results))
return default_answer_from_message_history()
```

What the model sees per turn:

- The RLM system prompt.
- A metadata message with context type and character lengths.
- The model's previous response.
- For each executed `repl` block, a user message containing the executed code, stdout/stderr, and a list of variable names.

The model does not automatically see the full `context` payload. It must inspect `context` from the REPL or ask submodels to process chunks.

### LM Handler

Every non-persistent completion creates an `LMHandler`.

Core behavior:

- Starts a `ThreadingTCPServer` on `127.0.0.1` and an OS-assigned port.
- Uses `4-byte big-endian length prefix + UTF-8 JSON` framing.
- Accepts single and batched requests.
- Routes by explicit `model` if registered, otherwise by depth:
  - default client for normal calls.
  - optional `other_backend_client` for depth `1`.
- Runs batched `llm_query_batched` requests concurrently with `asyncio.gather` and a semaphore.
- Aggregates usage summaries from registered clients.

Plugin implication: if you build an MCP or CLI wrapper, preserve this separation. Let sandboxed code call back to a host-side handler rather than embedding provider secrets inside the sandbox.

### Environment Contract

An environment must provide:

```python
setup()
load_context(context_payload)
execute_code(code) -> REPLResult
cleanup()  # strongly recommended
```

Executed code should receive:

```python
context
context_0, context_1, ...
history
llm_query
llm_query_batched
rlm_query
rlm_query_batched
FINAL_VAR
SHOW_VARS
custom tools
```

`REPLResult` carries:

- `stdout`
- `stderr`
- `locals`
- `execution_time`
- `rlm_calls`
- `final_answer`

### LocalREPL

`LocalREPL` is fast and useful for trusted workloads.

Implementation details:

- Runs `exec(code, combined, combined)` in the same Python process as the host RLM.
- Uses a persistent locals dictionary.
- Writes context into a temp file, then loads it into `context_0` and aliases `context`.
- Captures stdout/stderr under a thread lock.
- Restores reserved scaffold names after each execution.
- Supports custom tools. Callable tools go into globals; data values go into locals.
- Supports persistence for multi-turn RLM sessions.
- Supports compaction history by exposing `history`.
- Supports recursive `rlm_query` when `max_depth > 1`.

Security warning:

The builtins are only a soft guard. `eval`, `exec`, `compile`, and `input` are blocked, but `open` and `__import__` are present. Treat LocalREPL as arbitrary host code execution.

### IPythonREPL

`IPythonREPL` is the most useful environment for an RLM plugin meant for agentic developer workflows.

Modes:

- `kernel_mode="in_process"`: fast, same-process IPython shell, best-effort timeout only on Unix main thread via `SIGALRM`.
- `kernel_mode="subprocess"`: real `ipykernel` subprocess, hard per-cell timeout via `execute_interactive(timeout=...)` and kernel interrupt.

Implementation details:

- Supports cell magics and richer notebooks-style execution.
- In subprocess mode, uses a subcall broker with cell IDs so late subcalls from timed-out cells do not get attributed to a later cell.
- Has reentry guards to prevent a running cell from calling `execute_code` on its own parent REPL and corrupting bookkeeping.
- Supports `rlm_query` / `rlm_query_batched` with bounded concurrency.

Default plugin recommendation:

Use `ipython` subprocess mode for untrusted or long-running plugin workflows:

```python
RLM(
    environment="ipython",
    environment_kwargs={
        "kernel_mode": "subprocess",
        "cell_timeout": 30,
        "startup_timeout": 60,
        "subcall_timeout": 300,
    },
)
```

### Docker and Cloud Sandboxes

Docker, Modal, Prime, Daytona, and E2B move execution out of the host process.

Current implementation pattern:

- The sandbox runs Python code with persistent serialized state.
- The sandbox cannot call the model provider directly.
- A broker/proxy forwards `llm_query` and batched requests back to the host `LMHandler`.
- Context is loaded into sandbox state by file or JSON transfer.

Important current limitation:

In `RLM._spawn_completion_context`, recursive `subcall_fn` is passed only for `local` and `ipython` environments. The Docker/cloud scripts expose `llm_query` and `llm_query_batched`; they do not currently expose the full `rlm_query` child-loop surface. If your plugin needs true recursive child RLMs, choose `local` or `ipython`, or extend the isolated environment broker to support recursive subcalls.

## Implementation Review Findings

The current implementation is strong enough to build plugins around, but an agent should understand its boundaries before packaging it as infrastructure.

### Strengths

- The core loop is small and readable. `RLM.completion` owns orchestration; environments own execution; clients own provider calls.
- `LMHandler` keeps provider credentials and clients on the host side, which is the right pattern for sandboxes.
- The REPL contract is explicit and test-covered: context variables, `llm_query`, `rlm_query`, batched variants, `FINAL_VAR`, and trajectory metadata.
- `IPythonREPL` subprocess mode addresses several real production issues: hard cell timeouts, namespace isolation, stale subcall attribution, and reentry hazards.
- The logger captures enough metadata to reconstruct trajectories and inspect child calls.
- The package already includes budget, timeout, token, and consecutive-error stop conditions.
- Community activity is high and concentrated on practical gaps: provider support, caching, PDF workflows, parallelism, packaging, and security.

### Risks And Gaps

Treat these as plugin design constraints:

- `LocalREPL` is not a security boundary. It runs same-process `exec`, includes `open` and `__import__`, and has no hard timeout.
- Full recursive `rlm_query` support is currently local/IPython-oriented. Docker and cloud sandboxes need additional broker support for child RLM loops.
- Compaction is wired to environments that implement `append_compaction_entry`; in this repo, that is currently the local environment path. Do not assume `compaction=True` helps IPython or Docker unless you add support.
- `socket_recv` in `rlm/core/comms_utils.py` reads the 4-byte length prefix with a single `recv(4)`. TCP can legally return a partial prefix. The IPython subprocess bootstrap implements the more robust loop; the core helper should do the same in a hardening pass.
- Some provider clients and usage counters are called from threaded request handlers. If you increase parallelism, add locks or per-thread/per-request client handling where provider SDKs or usage accounting are not thread-safe.
- `RLM._fallback_answer` returns a raw string when `self.depth >= self.max_depth`, despite `completion()` otherwise returning `RLMChatCompletion`. Plugins should avoid exposing manually constructed non-root `RLM(depth=max_depth)` instances to users.
- The current default prompt is large and model-specific in style. The paper's negative results support maintaining provider/model-family prompt profiles.
- The visualizer is useful for development, but dependency CVE reports mean it should be kept current and treated as local-only unless reviewed.
- The docs are evolving. Prefer local code inspection over assuming old architecture docs are complete.

### Recommended Hardening Before Distribution

- Add a robust socket framing read loop to `comms_utils.socket_recv`.
- Add an RLM runner-level timeout that can kill or interrupt the execution environment, not only stop between RLM iterations.
- Add cache keys and idempotency controls around `llm_query` and `rlm_query`.
- Add a structured final-answer channel in the runner, even if the underlying RLM still uses `FINAL` / `FINAL_VAR`.
- Add explicit sandbox mode labels in plugin UI and output: `trusted-local`, `subprocess`, `container`, or `cloud`.
- Add provider compatibility tests for each model family the plugin advertises.

## How To Build An RLM Plugin

An RLM plugin should provide a reusable way for Claude Code or Codex to call an RLM runner. The plugin should not rely on the host agent to reimplement the loop from memory.

### Recommended Architecture

Use this shape:

```text
rlm-plugin/
  skills/
    rlm/
      SKILL.md
      references/
        rlm-runtime-contract.md
      scripts/
        rlm_run.py
        rlm_server.py        # optional MCP server
  scripts/
    rlm-run.ps1             # optional platform launcher
    rlm-run.sh              # optional platform launcher
  .mcp.json                 # optional MCP tool server config
  hooks/
    hooks.json              # optional lifecycle hooks
  assets/                   # optional logos/screenshots
  .claude-plugin/
    plugin.json             # Claude Code package
  .codex-plugin/
    plugin.json             # Codex package
```

The shared skill teaches the host agent when to delegate to RLM. The runner script or MCP server implements the actual loop using `rlms`.

### Skill Trigger Text

A good skill description is decisive and short:

```yaml
---
name: rlm
description: Use when a task has long context, many files, PDFs, logs, transcripts, corpus QA, or requires recursive decomposition over external context. Do not use for ordinary small edits.
---
```

Skill body should instruct the AI to:

- Prefer normal code search for small local tasks.
- Use RLM when raw context is too large, semantically distributed, or requires many independent subqueries.
- Stage context into files instead of the chat.
- Run `scripts/rlm_run.py` or the MCP `rlm_run` tool.
- Inspect trajectory logs when the answer looks weak.
- Never expose provider keys inside prompt text or sandboxed context.

### RLM Runner Interface

Give the host agent one stable command:

```bash
python scripts/rlm_run.py \
  --context path/to/context.txt \
  --prompt "Answer the user's question..." \
  --backend openai \
  --model gpt-5.4 \
  --environment ipython \
  --max-depth 2 \
  --max-iterations 12 \
  --max-timeout 300 \
  --log-dir .rlm/logs
```

The runner should:

- Validate Python `>=3.11`.
- Import `from rlm import RLM`.
- Load context from files, directories, PDFs, logs, or JSON.
- Redact obvious secrets before sending chunks to submodels.
- Choose `ipython` subprocess mode unless user asks for faster trusted local execution.
- Set `max_depth`, `max_iterations`, `max_timeout`, `max_errors`, and optionally `max_budget`.
- Save trajectory logs.
- Print compact JSON by default:

```json
{
  "ok": true,
  "answer": "...",
  "execution_time": 123.4,
  "usage_summary": {},
  "trajectory_log": ".rlm/logs/rlm_....jsonl"
}
```

### MCP Server Interface

For Claude Code and Codex, MCP is the cleanest cross-agent runtime surface. Expose these tools:

```text
rlm_run
  input:
    prompt: string
    context_paths: string[]
    context_text: string optional
    backend: string optional
    model: string optional
    environment: string optional
    max_depth: integer optional
    max_iterations: integer optional
    max_timeout: number optional
    max_budget: number optional
  output:
    answer: string
    usage_summary: object
    trajectory_id: string

rlm_inspect_trajectory
  input:
    trajectory_id: string
  output:
    iterations: object[]
    subcalls: object[]
    warnings: string[]

rlm_health
  output:
    python_version: string
    rlms_version: string
    available_backends: string[]
    sandbox_support: object
```

Prefer MCP when the plugin is expected to be reused by multiple agents or teams. Prefer a simple script for local experiments.

## Claude Code Plugin Packaging

Claude Code plugins use `.claude-plugin/plugin.json`. Components live at the plugin root, not inside `.claude-plugin/`.

Claude Code supports:

- `skills/`
- `commands/` as legacy flat Markdown skills
- `agents/`
- `hooks/hooks.json`
- `.mcp.json`
- `.lsp.json`
- `monitors/monitors.json`
- `bin/`
- `settings.json`

Minimal RLM plugin:

```text
rlm-claude/
  .claude-plugin/
    plugin.json
  skills/
    rlm/
      SKILL.md
      scripts/
        rlm_run.py
  .mcp.json
```

`rlm-claude/.claude-plugin/plugin.json`:

```json
{
  "name": "rlm",
  "description": "Recursive Language Model workflows for long-context analysis",
  "version": "0.1.0",
  "author": { "name": "Your team" },
  "skills": "./skills/",
  "mcpServers": "./.mcp.json"
}
```

Development test command:

```bash
claude --plugin-dir ./rlm-claude
```

Operational notes:

- Installed plugin skills are namespaced, for example `/rlm:rlm`.
- Claude Code plugin `CLAUDE.md` at plugin root is not loaded as project context. Put instructions in a skill or agent.
- Use `${CLAUDE_PLUGIN_ROOT}` in hooks, MCP server configs, and scripts.
- Marketplace-installed plugins are copied into `~/.claude/plugins/cache`; do not rely on `../shared` paths unless using symlinks deliberately.

## Codex Plugin Packaging

Codex plugins use `.codex-plugin/plugin.json`. Codex plugins bundle skills, apps, MCP servers, hooks, lifecycle config, and assets.

Codex supports plugin discovery through:

- the curated marketplace
- repo marketplace: `$REPO_ROOT/.agents/plugins/marketplace.json`
- Claude-style marketplace: `$REPO_ROOT/.claude-plugin/marketplace.json`
- personal marketplace: `~/.agents/plugins/marketplace.json`

Installed local plugins are copied to:

```text
~/.codex/plugins/cache/$MARKETPLACE_NAME/$PLUGIN_NAME/$VERSION/
```

Minimal RLM plugin:

```text
rlm-codex/
  .codex-plugin/
    plugin.json
  skills/
    rlm/
      SKILL.md
      scripts/
        rlm_run.py
  .mcp.json
  hooks/
    hooks.json
  assets/
```

`rlm-codex/.codex-plugin/plugin.json`:

```json
{
  "name": "rlm",
  "version": "0.1.0",
  "description": "Recursive Language Model workflows for long-context analysis",
  "author": {
    "name": "Your team"
  },
  "skills": "./skills/",
  "mcpServers": "./.mcp.json",
  "hooks": "./hooks/hooks.json",
  "interface": {
    "displayName": "RLM",
    "shortDescription": "Long-context recursive analysis",
    "longDescription": "Run Recursive Language Model workflows over files, corpora, logs, and PDFs without stuffing all context into the model prompt.",
    "developerName": "Your team",
    "category": "Productivity",
    "capabilities": ["Read", "Write"],
    "brandColor": "#10A37F",
    "defaultPrompt": [
      "Use RLM to answer questions over these logs.",
      "Use RLM to review this large corpus."
    ]
  }
}
```

Repo-local marketplace entry:

```json
{
  "name": "local-rlm",
  "interface": {
    "displayName": "Local RLM Plugins"
  },
  "plugins": [
    {
      "name": "rlm",
      "source": {
        "source": "local",
        "path": "./plugins/rlm"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

Codex-specific operational notes:

- Skills are available in CLI, IDE extension, and Codex app.
- Codex uses progressive disclosure: it initially sees skill name, description, and path, then reads full `SKILL.md` only when selected.
- Codex caps the initial skills list budget. Front-load the trigger words in the `description`.
- Codex hooks are behind `[features] codex_hooks = true` and are useful for deterministic lifecycle scripts, but they are not a complete enforcement boundary.
- Codex AGENTS.md discovery is limited by `project_doc_max_bytes`, 32 KiB by default. Do not rely on a huge `AGENTS.md` to teach RLM. Use a skill.

## Cross-Platform Plugin Strategy

Build one shared skill and two manifests.

Use:

```text
plugins/rlm/
  .claude-plugin/plugin.json
  .codex-plugin/plugin.json
  skills/rlm/SKILL.md
  skills/rlm/scripts/rlm_run.py
  .mcp.json
```

Keep platform-specific differences small:

- Claude Code: namespaced slash skills and `${CLAUDE_PLUGIN_ROOT}` paths.
- Codex: `.codex-plugin` manifest, `.agents/plugins/marketplace.json`, skill `name` required, plugin cache path, optional `interface`.
- Both: MCP tool interface can be the same if the process can discover its plugin root.

## Practical Improvements From Community Signals

These are the highest-value improvements to implement in RLM plugins or upstream RLM forks.

### 1. Use parallelism deliberately

The paper notes sequential subcalls are slow. The current repo has batched `llm_query_batched` and parallel `rlm_query_batched` for local/IPython. Community PRs also target parallel subcalls and thread safety.

Plugin action:

- Teach the skill to batch independent chunk prompts.
- Add `--max-concurrent-subcalls`.
- Use semaphores around recursive calls.
- Preserve output order.
- Log per-subcall duration.

### 2. Add caching and deduplication

Open community work targets memoization and prompt caching. RLM workloads repeat chunk summaries, metadata extraction, and aggregation prompts.

Plugin action:

- Cache `llm_query` by `(provider, model, prompt_hash, tool_version)`.
- Cache parsed document chunks by file digest.
- Cache trajectory summaries.
- Detect duplicate subqueries before sending them.
- Prefer provider-side prompt caching when available.

### 3. Add task-specific loaders without task-specific reasoning

PDF, tables, medical charts, and large logs appear repeatedly in community questions and PRs. The RLM algorithm can remain task-agnostic while the plugin provides better loaders.

Plugin action:

- Add document ingestion helpers:
  - PDF text extraction by page.
  - Table extraction preserving row/column structure.
  - OCR fallback.
  - page-span citation metadata.
  - chunk search by keyword or embeddings.
- Put helpers in REPL custom tools instead of bloating the system prompt.

### 4. Improve provider compatibility

Issues mention local Qwen-style chat template problems, z.ai/GLM support, Azure Anthropic, Cohere, MiniMax, Vercel sandbox, and Responses API migration designs.

Plugin action:

- Treat provider clients as adapters with test fixtures.
- Keep prompt/message conversion provider-specific.
- For local/open-source models, wrap prompts in the correct chat template.
- Expose a `--provider-profile` option that changes system prompt and final-answer guardrails per model family.
- Validate both string prompts and message-list prompts.

### 5. Harden final-answer protocol

The paper and tests both show final-answer parsing is a failure point.

Plugin action:

- Prefer `FINAL_VAR(variable)` after creating a variable in code.
- Add a postprocessor that rejects final answers that look like plans.
- Add a retry message when `FINAL_VAR` references a missing variable.
- Consider a structured sentinel file or JSON result channel for runner-controlled completions, rather than relying only on model-visible tags.

### 6. Make installation fail loudly

Issue #113 reports that Python 3.10 can install an old stub package instead of the real `rlms` package.

Plugin action:

- Check `sys.version_info >= (3, 11)` before import.
- Run `python -c "from rlm import RLM"` during setup.
- Print exact remediation:

```text
RLM requires Python 3.11+. Create a Python 3.11 or 3.12 environment and reinstall:
python -m pip install --upgrade rlms
```

### 7. Do not present LocalREPL as a sandbox

The README says local execution is not for production. Code confirms `open` and `__import__` are available.

Plugin action:

- Default to `ipython` subprocess or Docker for untrusted content.
- Require explicit opt-in for same-process `local`.
- Add red-team tests for file reads, network calls, long sleeps, and runaway loops.
- For Claude/Codex hooks, remember hooks are guardrails, not complete enforcement boundaries.

### 8. Keep the visualizer secure

Issue #97 reports dependency CVEs in the visualizer.

Plugin action:

- Treat trajectory visualization as a local dev tool unless dependencies are current.
- Do not expose visualizer logs containing prompts or secrets over public networks.
- Sanitize logs before sharing.

### 9. Add multimodal subquery support

Issue #117 asks for vision-language model support for subqueries.

Plugin action:

- Represent context chunks as typed parts, not only strings:

```json
{
  "type": "image",
  "path": "page-003.png",
  "caption": "PDF page 3 render"
}
```

- Extend `llm_query` to accept message content arrays where the provider supports it.
- Add PDF page rendering and image chunk references.

### 10. Prefer a long-running service for repeated plugin use

The discussions include an API serving layer idea. Plugins will often run multiple RLM tasks in a session.

Plugin action:

- Offer an optional local daemon/MCP server.
- Reuse loaded models, chunk indexes, caches, and sandboxes.
- Expose health/status/log tools.
- Keep one-off CLI mode for simple installation.

## AI Agent Build Checklist

When asked to build an RLM plugin:

1. Inspect the target host: Claude Code, Codex, or both.
2. Create a skill first. The skill is the model-facing workflow contract.
3. Create a deterministic runner or MCP server. Do not leave RLM loop details only in prose.
4. Validate Python version and `rlms` import.
5. Choose default environment:
   - trusted local speed: `local`
   - safer general default: `ipython` subprocess
   - stronger isolation: Docker/cloud sandbox
6. Add context ingestion:
   - file list
   - directory traversal with ignore rules
   - PDF/page/table handling if relevant
   - max bytes and redaction
7. Add budgets:
   - `max_depth`
   - `max_iterations`
   - `max_timeout`
   - `max_errors`
   - optional `max_budget`
8. Add logging:
   - JSON answer
   - JSONL trajectory
   - summarized usage
9. Add tests:
   - small context smoke test with mock LM
   - missing Python version/import failure
   - long context chunking
   - batching preserves order
   - final-answer retry on bad `FINAL_VAR`
   - no host file read in sandbox mode
10. Package:
   - Claude Code: `.claude-plugin/plugin.json`
   - Codex: `.codex-plugin/plugin.json` plus marketplace entry if needed
11. Document exact invocation for the host agent.

## Minimal Runner Skeleton

Use this as a shape, not as complete production code:

```python
import argparse
import json
import sys
from pathlib import Path


def fail(message: str, code: int = 1) -> None:
    print(json.dumps({"ok": False, "error": message}), file=sys.stderr)
    raise SystemExit(code)


def main() -> None:
    if sys.version_info < (3, 11):
        fail("RLM requires Python 3.11 or newer.")

    try:
        from rlm import RLM
        from rlm.logger import RLMLogger
    except Exception as exc:
        fail(f"Could not import rlms package: {exc}")

    parser = argparse.ArgumentParser()
    parser.add_argument("--context", action="append", default=[])
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--backend", default="openai")
    parser.add_argument("--model", required=True)
    parser.add_argument("--environment", default="ipython")
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-iterations", type=int, default=12)
    parser.add_argument("--max-timeout", type=float, default=300.0)
    parser.add_argument("--log-dir", default=".rlm/logs")
    args = parser.parse_args()

    context_parts = []
    for item in args.context:
        p = Path(item)
        if p.is_file():
            context_parts.append({"path": str(p), "content": p.read_text(errors="replace")})
        else:
            fail(f"Context path not found or unsupported: {item}")

    logger = RLMLogger(log_dir=args.log_dir)
    env_kwargs = {}
    if args.environment == "ipython":
        env_kwargs = {
            "kernel_mode": "subprocess",
            "cell_timeout": 30,
            "startup_timeout": 60,
            "subcall_timeout": args.max_timeout,
        }

    rlm = RLM(
        backend=args.backend,
        backend_kwargs={"model_name": args.model},
        environment=args.environment,
        environment_kwargs=env_kwargs,
        max_depth=args.max_depth,
        max_iterations=args.max_iterations,
        max_timeout=args.max_timeout,
        max_errors=4,
        logger=logger,
    )

    try:
        result = rlm.completion(context_parts, root_prompt=args.prompt)
    finally:
        rlm.close()

    print(json.dumps({
        "ok": True,
        "answer": result.response,
        "execution_time": result.execution_time,
        "usage_summary": result.usage_summary.to_dict(),
        "trajectory_log": logger.log_file_path,
    }, default=str))


if __name__ == "__main__":
    main()
```

## Prompting Rules For RLM Controller Models

Put these rules in the RLM system prompt or skill references:

- First inspect `context` or context metadata in REPL. Do not answer from metadata alone.
- Use `llm_query_batched` for independent chunk extraction.
- Use `rlm_query` only for subtasks needing multi-step reasoning.
- Save intermediate answers in named variables.
- Print short diagnostics, not huge objects.
- If output is truncated, query a variable with a submodel or write a targeted summarizer.
- Use `FINAL_VAR(name)` only after creating `name`.
- If a subcall returns "Error:", branch and recover.
- Avoid deeply recursive fanout unless bounded by budget and concurrency.

## Validation Matrix

An RLM plugin is not ready until these pass:

| Test | Expected result |
| --- | --- |
| Small string context | returns correct answer without unnecessary recursion |
| 1 MB text context | chunks and batches subqueries |
| Missing context file | fails with JSON error |
| Python 3.10 | clear unsupported-version error |
| Bad `FINAL_VAR` | RLM continues or returns actionable error |
| `local` environment file read attempt | documented as allowed only in trusted mode |
| `ipython` subprocess sleep beyond timeout | cell interrupted and later cell still works |
| Duplicate subquery prompts | cache hit or deduplication log |
| Provider without usage data | usage warning, no crash if possible |
| Visualizer disabled | logs still inspectable as JSONL |

## Open Design Questions

These are not settled by the paper or current implementation:

- Should `FINAL` / `FINAL_VAR` become a structured side channel instead of model text?
- Should isolated environments support full recursive `rlm_query`, not only `llm_query`?
- Should RLM routing use different models by depth, task type, chunk size, or confidence?
- How should prompt caching be represented across provider clients?
- Should trajectory datasets be public and versioned for distillation?
- What is the right multimodal context representation for VLM subqueries?
- How should a plugin expose cost estimates before running?

## Practical Defaults

Use these defaults unless the user gives stronger constraints:

```python
RLM(
    backend="openai",
    backend_kwargs={"model_name": "gpt-5.4"},
    environment="ipython",
    environment_kwargs={
        "kernel_mode": "subprocess",
        "cell_timeout": 30,
        "startup_timeout": 60,
        "subcall_timeout": 300,
    },
    max_depth=2,
    max_iterations=12,
    max_timeout=300,
    max_errors=4,
    max_concurrent_subcalls=4,
    compaction=False,
)
```

Adjust:

- `max_depth=1` for cost-sensitive extraction.
- `max_depth=3` only for complex decomposition with strict concurrency/budget caps.
- `environment="local"` only for trusted code and speed.
- `environment="docker"` or cloud sandbox when prompts or documents may be adversarial.
- Enable `compaction=True` only with an environment that supports compaction history, or implement that support first.

## References

- RLM repository: https://github.com/alexzhang13/rlm
- RLM paper: https://arxiv.org/abs/2512.24601
- RLM documentation: https://alexzhang13.github.io/rlm/
- RLM blog: https://alexzhang13.github.io/blog/2025/rlm/
- Claude Code plugin creation: https://code.claude.com/docs/en/plugins
- Claude Code plugin reference: https://code.claude.com/docs/en/plugins-reference
- Codex plugins overview: https://developers.openai.com/codex/plugins
- Codex plugin build guide: https://developers.openai.com/codex/plugins/build
- Codex AGENTS.md guide: https://developers.openai.com/codex/guides/agents-md
- Codex hooks: https://developers.openai.com/codex/hooks
- Codex MCP: https://developers.openai.com/codex/mcp
- Codex skills: https://developers.openai.com/codex/skills
- RLM GitHub issues and PRs reviewed:
  - Python 3.10 install fallback: https://github.com/alexzhang13/rlm/issues/113
  - Visualizer CVEs: https://github.com/alexzhang13/rlm/issues/97
  - Non-deterministic OpenAI JSON body error: https://github.com/alexzhang13/rlm/issues/144
  - z.ai / GLM support signal: https://github.com/alexzhang13/rlm/issues/142
  - VLM subquery support: https://github.com/alexzhang13/rlm/issues/117
  - PDF-focused prompt/helpers PR: https://github.com/alexzhang13/rlm/pull/151
  - Parallel subcalls PR: https://github.com/alexzhang13/rlm/pull/136
  - Prompt caching/shared handler PR: https://github.com/alexzhang13/rlm/pull/126
  - Claude Code CLI client PR: https://github.com/alexzhang13/rlm/pull/125
  - LLM call memoization PR: https://github.com/alexzhang13/rlm/pull/118
  - Shared sub-client instantiation PR: https://github.com/alexzhang13/rlm/pull/159
