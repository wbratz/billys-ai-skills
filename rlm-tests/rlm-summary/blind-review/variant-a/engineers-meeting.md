# Recursive Language Models (RLM) — Engineering Meeting (30 min)

**Source:** Zhang, Kraska, Khattab — "Recursive Language Models" — ICML 2026 (arXiv:2512.24601v2)
**Audience:** Engineers evaluating adoption
**Goal:** Understand what RLM is, how it works, when (and when not) to use it

---

## Agenda (30 min)

| Time | Topic |
|------|-------|
| 0:00–0:03 | TL;DR and problem framing |
| 0:03–0:10 | How RLM actually works (architecture + algorithm) |
| 0:10–0:18 | Benchmarks, results, cost/latency profile |
| 0:18–0:24 | Implementation considerations and failure modes |
| 0:24–0:30 | When to adopt + Q&A |

---

## 1. TL;DR (3 min)

- **What:** An inference-time scaffold where the user's long prompt lives as a Python variable in a REPL, and the LLM writes code that peeks at, chunks, and recursively calls sub-LLMs on slices of it. The model only ever sees metadata + intermediate variables in its own context.
- **Why:** Frontier LLMs degrade sharply on dense long-context tasks ("context rot"). RLM decouples *effective* context length from architectural context window. They demonstrate processing inputs up to **two orders of magnitude beyond** native windows.
- **Headline result:** GPT-5 on OOLONG-Pairs (pairwise reasoning over 32K tokens) goes from **0.1% → 58.0%**. On BrowseComp-Plus (6M–11M token corpus), **0% → 91.3%**, at median cost lower than naive ingestion (~$0.99/task).
- **Status:** Research prototype. Code at `github.com/alexzhang13/rlm` (pip package `rlms`). Works zero-shot with GPT-5 and Qwen3-Coder-480B; small models need fine-tuning.

---

## 2. How RLM Works (7 min)

### 2.1 The three design choices that matter

The paper is explicit that prior agent/tool-use scaffolds miss three things — these are the load-bearing ideas:

1. **Symbolic handle to the prompt.** The prompt is *never* placed into the LLM's context window. It is bound to a Python variable (`context`) inside a REPL the model can drive via code.
2. **Symbolic code generation, not autoregressive answering.** The model emits Python; the REPL executes it. Final answers are emitted via `FINAL(...)` or `FINAL_VAR(var_name)` — which lets outputs be arbitrarily long (read from a variable, not generated token-by-token at the end).
3. **Programmatic recursion, not task enumeration.** Because the model writes code, it can loop `llm_query(slice)` over O(|P|) or O(|P|²) slices without having to enumerate sub-tasks in natural language.

### 2.2 Algorithm (paraphrased pseudocode)

```
state ← InitREPL(prompt = P)            # P bound to `context` variable
state ← AddFunction(state, llm_query)   # sub-LM available as a function
hist  ← [Metadata(state)]               # length, prefix, schema — NOT the prompt
while True:
    code  ← LLM(hist)                   # root LM emits Python
    state, stdout ← REPL(state, code)
    hist  ← hist ∥ code ∥ Metadata(stdout)   # truncated stdout, not full results
    if state[Final] is set:
        return state[Final]
```

Key invariants:
- The root LM's context grows only with **code + truncated metadata**, not with prompt contents or sub-call outputs.
- Sub-call results land in REPL variables, which the model references symbolically (`FINAL_VAR("answers")`).
- Max recursion depth in published experiments is **1** (sub-calls are plain LMs, not nested RLMs), though deeper recursion is supported.

### 2.3 Typical emergent pattern

```python
chunk_size = len(context) // 10
answers = []
for i in range(10):
    chunk = "\n".join(context[i*chunk_size:(i+1)*chunk_size])
    answers.append(llm_query(f"Analyze: {chunk} ..."))
final = llm_query(f"Aggregate: {answers} ...")
FINAL(final)
```

Other observed strategies: regex pre-filtering ("festival", "La Union" style keyword search), line-by-line semantic transform on dense tasks, and variable-buffer accumulation for multi-part answers.

### 2.4 Why this beats naive long-context and tool-use agents

- vs. **naive long-context**: Avoids "context rot" — model never re-attends over millions of tokens at once.
- vs. **ReAct / CodeAct + BM25**: BM25 retrieval discards info; RLM can perform exhaustive O(n²) sweeps. On OOLONG-Pairs CodeAct+BM25 hits 24.7% vs RLM 58.0%.
- vs. **Summary-agent baselines**: Summary agents lose detail and fail on dense aggregation (0.1% on OOLONG-Pairs).

---

## 3. Benchmarks and Performance (8 min)

### 3.1 Benchmarks chosen for complexity coverage

| Benchmark | Task complexity | Scale | What it stresses |
|---|---|---|---|
| S-NIAH | O(1) | 8K–262K tokens | Needle-in-haystack retrieval |
| BrowseComp-Plus | O(1) over docs | 6M–11M tokens | Multi-hop QA over 1K docs |
| OOLONG | O(n) | 131K tokens | Aggregate every entry |
| OOLONG-Pairs | O(n²) | 32K tokens | Pairwise reasoning, F1 scored |
| CodeQA | O(1) over files | 23K–4.2M tokens | Repo-scale code understanding |

### 3.2 Headline numbers (Table 1)

**GPT-5 (root) + GPT-5-mini (sub):**
- CodeQA: 24.0% → **62.0%**
- BrowseComp-Plus: 0.0% → **91.3%** (base fails entirely — doesn't fit)
- OOLONG: 44.0% → **56.5%**
- OOLONG-Pairs: 0.1% → **58.0%**

**Qwen3-Coder-480B-A35B:**
- CodeQA: 20.0% → 56.0%
- BrowseComp-Plus: 0.0% → 44.7%
- OOLONG-Pairs: 0.1% → 23.1%

**Fine-tuned RLM-Qwen3-8B** (1K SFT samples distilled from Qwen3-Coder-480B RLM trajectories on LongBenchPro, 48 H100-hours): **+28.3% average** over base Qwen3-8B.

### 3.3 Cost and latency

- **Median cost** of RLM(GPT-5) on BrowseComp-Plus: **~$0.99/task** vs an extrapolated $1.50–$2.75 for direct 6–11M token ingestion (which also returns 0% accuracy).
- **Tail cost** is the watch-out: 95th percentile up to ~3× median due to trajectory-length variance.
- **Latency**: Sub-calls are synchronous in the reference implementation. Wall-clock can be substantially worse than a single LLM call. Async sub-calls are listed as future work — easy win for any production reimplementation.

### 3.4 When RLM is *not* worth it

- Simple retrieval where base model already succeeds (S-NIAH at moderate scales).
- Latency-critical paths (chat, autocomplete).
- Tasks dominated by output generation rather than input comprehension.

---

## 4. Implementation Considerations (6 min)

### 4.1 What you'd need to stand this up

- A **sandboxed Python REPL** with persistent state per session.
- An `llm_query(prompt, model=..., max_chars=~500K)` function exposed to the REPL.
- A **driver loop** that: sends history to root LM → executes returned code → captures truncated stdout → appends metadata → checks for `FINAL`/`FINAL_VAR` sentinels.
- **Sentinel parsing** for `FINAL(...)` and `FINAL_VAR(var_name)`. The paper reports this is brittle; ~16% of fine-tuning samples had `FINAL()` template mistakes and 13% misused the variable form. Plan to programmatically repair.
- **stdout truncation policy** to keep root context bounded.
- **Sub-call concurrency**: do async; the paper's sync version leaves real latency on the table.

### 4.2 Tuning knobs

- Root vs sub model split (GPT-5 / GPT-5-mini works; cost-capability tradeoff).
- Max sub-call payload size (~500K chars / ~125K tokens in their setup).
- Max root iterations (≈ K/c where K is context window).
- Recursion depth (1 in paper; deeper unexplored).
- Anti-runaway prompts (Qwen3-Coder needed an explicit warning to stop making thousands of sub-calls).

### 4.3 Failure modes documented in Appendix B

- **Weak coding ability** → can't drive the REPL (Qwen3-8B base fails without fine-tuning).
- **Reasoning models exhaust output token budgets** mid-trajectory (Qwen3-235B thinking mode).
- **Final-answer tag confusion** — distinguishing thought from final output is fragile.
- **Prompt-portability is poor** — GPT-5 prompt does not transfer cleanly to Qwen3-Coder.

### 4.4 Adoption posture

- **Easy wins:** Internal tools where input is huge and accuracy matters more than latency (repo Q&A, doc-corpus analytics, eval pipelines).
- **Build vs. buy:** The `rlms` package gives a runnable starting point; production needs sandboxing, async, retries, observability, and cost caps.
- **Model choice:** Strongest results require a frontier model with strong coding ability as the root. Sub-calls can be cheaper models.

---

## 5. Q&A Prompts (6 min)

- Where in our stack would RLM beat our current retrieval pipeline?
- Are we willing to accept p95 cost/latency 2–3× median for accuracy that goes from 0% to >50% on currently-broken use cases?
- Do we have a sandboxed code-execution environment that can host the REPL safely?
- Which of our models has strong-enough coding ability to be the root? Do we need a fine-tune to deploy on smaller/cheaper models?
- Could we collapse RLM into a single agent step in our existing orchestrator, or does it warrant a new service?
- Async sub-calls are listed as future work — is this a 1-week build for us and a competitive moat?

---

## Key Takeaways

1. RLM is **not a new model** — it's an inference scaffold that any team can build today on top of existing LLM APIs.
2. The big unlock is **dense long-context tasks** that current models fail on entirely (0% → 50–90%).
3. **Median cost is competitive**; tail cost is real and needs governance.
4. **Production gaps:** sandboxing, async sub-calls, sentinel parsing robustness, prompt-per-model tuning.
5. The paper itself frames RLM trajectories as a learnable form of reasoning — expect this to merge with model training, not stay purely inference-time.
