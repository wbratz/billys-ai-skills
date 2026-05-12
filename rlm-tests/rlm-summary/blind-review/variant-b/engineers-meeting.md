# Engineering Meeting — Recursive Language Models (RLM)

**Duration:** 30 minutes
**Audience:** Engineers, ML/infra, platform
**Source:** Zhang, Kraska, Khattab — *Recursive Language Models* (arXiv:2512.24601v2, ICML 2026) — https://arxiv.org/html/2512.24601v2
**Code:** https://github.com/alexzhang13/rlm

---

## Agenda (30 min)

| Time | Topic |
|---|---|
| 0:00–0:05 | What RLM is (one slide) |
| 0:05–0:13 | How it actually works — architecture walkthrough |
| 0:13–0:21 | Benchmarks: where RLM beats long-context models, where it doesn't |
| 0:21–0:26 | Cost, latency, failure modes |
| 0:26–0:30 | When to adopt / pilot proposals + Q&A |

---

## 1. What RLM is (5 min)

Paper definition: *"An RLM is an inference-time scaffold around a base language model that treats the user prompt as part of the environment without giving up the ability to densely process its content through different calls to the model."*

Plain version: instead of stuffing a 500K-token document into a model's context window, RLM gives the model a **Python REPL** with the document loaded as a variable. The model writes code to slice/grep/filter, fires sub-LLM calls on chunks, and synthesizes an answer. Only short summaries — not the raw content — ever enter the controller's prompt.

> Key reframe: RLM is **not** a longer context window. It's a control loop around a model.

---

## 2. Architecture walkthrough (8 min)

```
┌────────────────────────────────────────────┐
│  Root controller LLM (e.g. GPT-5, Sonnet)  │
│  - Sees only its own REPL turns            │
│  - Writes Python code each iteration       │
└──────────────────┬─────────────────────────┘
                   │ exec code
                   ▼
┌────────────────────────────────────────────┐
│  Python REPL (sandboxed)                   │
│  - prompt_var = "<huge text>"  ← never seen by controller
│  - llm_query(text, q) → sub-LLM call       │
│  - regex, slicing, batching primitives     │
└──────────────────┬─────────────────────────┘
                   │ subcalls
                   ▼
┌────────────────────────────────────────────┐
│  Sub-LLMs (cheap: Haiku, smaller models)   │
│  - One chunk in, structured extraction out │
└────────────────────────────────────────────┘
```

Mechanics worth noting:
- **stdout is truncated** before re-entering the controller's history (length + prefix metadata only). This is the trick that keeps the controller's window small even as it processes huge data.
- **Termination**: model emits `FINAL(...)` or `FINAL_VAR(name)`. Authors note `FINAL_VAR` is more reliable — bare `FINAL` parsing is brittle.
- **Recursion**: in the paper, single-level (controller → leaf workers). Deeper recursion is open work.
- **Sandbox**: IPython subprocess is the safe default — hard cell timeouts, kernel isolation.

---

## 3. Benchmarks (8 min)

Numbers from the paper (verbatim):

**GPT-5 + RLM vs. base GPT-5 (long context):**
| Benchmark | Base GPT-5 | GPT-5 + RLM |
|---|---|---|
| OOLONG | 44.0% | **56.5%** |
| OOLONG-Pairs (F1) | 0.1 | **58.0** |
| BrowseComp-Plus (1K docs) | 0.0% (hit input limits) | **91.3%** |
| CodeQA | 24.0% | **62.0%** |

**Open-weight Qwen3-Coder-480B + RLM:**
- CodeQA: 56.0% vs 20.0%
- OOLONG: 48.0% vs 36.0%

**Fine-tuned 8B (RLM-Qwen3-8B):** +28.3% avg over base; approaches GPT-5 on three long-context tasks despite being 60× smaller.

Where RLM is weakest: information-dense tasks (quadratic-ish blowup) lose more ground than sparse retrieval (NIAH-style).

---

## 4. Cost, latency, failure modes (5 min)

**Cost** (BrowseComp-Plus average):
- GPT-5 + RLM: **$0.99**
- Direct GPT-5 ingestion (extrapolated): $1.50–$2.75
- ~3× cheaper than summarization-agent baselines

But: **high variance** — outlier runs can blow past direct-ingestion cost when the controller loops a lot.

**Latency:** the reference impl uses **sequential** sub-calls. Async fan-out is left to the implementer and is the easy first win.

**Failure modes to plan for:**
1. Token exhaustion mid-trajectory — reasoning models eat output tokens fast.
2. Brittle `FINAL()` parsing — sometimes the model emits its plan as the answer.
3. Sub-call cost spikes on chunky inputs — needs guardrails (max iterations, max budget).
4. Smaller controllers (≤8B) fail without fine-tuning — they can't write good orchestration code.

---

## 5. When to adopt / pilot proposals (4 min) + Q&A

**Adopt RLM when:**
- Inputs routinely exceed ~50KB or span many files/PDFs.
- Tasks need semantic access across the whole input (not just retrieve-and-answer).
- Per-task cost matters more than per-call latency.

**Don't adopt when:**
- Input fits easily in context and the model handles it well.
- Latency budget is sub-second.
- Sub-call pricing wipes the savings (some closed APIs).

**Pilot ideas for our stack:**
- Log triage agent over multi-GB incident archives.
- Codebase Q&A over repos that bust context.
- Document-pile classification (legal, support tickets, RFPs).

**Discussion prompts:**
- Which long-context features have we *not* shipped because the model couldn't hold the input? Could RLM unblock them?
- What's our sub-call provider cost? Does Haiku/Flash pricing make the math work for us?
- Build vs. adopt `rlms` package? What's the cost of a thin in-house controller?
- Where's the right sandbox boundary — IPython subprocess, Docker, Modal?

---

## Key takeaways

1. RLM is a **control loop**, not a bigger model. The prompt lives in a Python variable; the model writes code over it.
2. On long-context benchmarks, **adding RLM to GPT-5 outperforms GPT-5 alone by large margins** (e.g., 44% → 56.5% on OOLONG; 0% → 91.3% on BrowseComp-Plus at 1K docs).
3. **Cheaper on average** than direct long-context use, but **variance is high** — set budget caps.
4. **Implementation cost is modest** (~hundreds of LOC of orchestration), but coding-capable controllers and reliable termination need care.
5. Best near-term wins for us are tasks that today are blocked by context limits, not tasks that already work.
