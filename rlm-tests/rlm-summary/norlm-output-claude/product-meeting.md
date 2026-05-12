# Recursive Language Models (RLM) — Product Owner Meeting (30 min)

**Source:** Zhang, Kraska, Khattab — "Recursive Language Models" — ICML 2026 (arXiv:2512.24601v2)
**Audience:** Product owners working with engineering
**Goal:** Decide which features RLM makes feasible, what tradeoffs to expect, and what to negotiate with engineering

---

## Agenda (30 min)

| Time | Topic |
|------|-------|
| 0:00–0:04 | Plain-language overview |
| 0:04–0:10 | Capabilities unlocked — what features become possible |
| 0:10–0:18 | Tradeoffs: cost, latency, accuracy |
| 0:18–0:24 | What to discuss with engineering |
| 0:24–0:30 | Roadmap implications + Q&A |

---

## 1. Plain-Language Overview (4 min)

Today's LLMs have a context window — the amount of text they can "see" at once. Even when the window is large, quality drops sharply when the input is dense (lots of important facts spread throughout) or when the input is larger than the window. This blocks a whole class of features: "ask anything about our entire codebase," "summarize 1,000 customer interviews," "find every contract that conflicts with this clause," etc.

**RLM (Recursive Language Models)** is a technique where the LLM is given the long input *as a file it can browse* rather than as text stuffed into its head. The model writes small programs that chunk the input, look at the relevant parts, and call *itself* recursively on pieces. The final answer is assembled from those pieces.

Result: tasks that frontier models score **0% on** today (because the input is too big or too dense) can be solved at **50–90% accuracy**, often at *similar* cost to a single big call — and on benchmarks the authors built, RLM handled inputs **100× larger** than the model's native window.

---

## 2. Capabilities Unlocked (6 min)

These are feature categories that move from "impossible / unreliable" to "tractable":

### 2.1 Whole-corpus question answering
- Examples: "Analyze our entire codebase," "Synthesize findings across all customer support tickets this quarter," "Find every place this policy is referenced across our document store."
- Why now: BrowseComp-Plus (a 1,000-document, 6M–11M token benchmark) went from **0% → 91.3%** with RLM on GPT-5.

### 2.2 Exhaustive cross-document reasoning
- Examples: contract compliance review across the full deal book, dedup/conflict detection across knowledge bases, pairwise comparison of candidates/products/cases.
- Why now: pairwise (quadratic) reasoning task OOLONG-Pairs went from **0.1% → 58%**. Pairwise comparisons across thousands of items were previously infeasible.

### 2.3 Long-horizon research assistants
- Examples: deep-research products that ingest entire topic domains, due diligence assistants, literature reviewers.
- Why now: the model can browse rather than memorize, so input size no longer caps depth of analysis.

### 2.4 Repo-scale code understanding
- Examples: architectural Q&A across millions of tokens of code, migration planning, cross-file refactor proposals.
- Why now: CodeQA scores **24% → 62%** with RLM on GPT-5 over 23K–4.2M token repos.

### 2.5 Long-output, structured deliverables
- Examples: full audit reports, multi-section summaries, generated dossiers.
- Why now: RLM produces the output by *reading from a variable* rather than generating it as one long completion, so output length is no longer a hard ceiling.

---

## 3. Tradeoffs (8 min)

### 3.1 Accuracy — large gains, but only on the right tasks

| Task type | Before (GPT-5 base) | With RLM | Use it? |
|---|---|---|---|
| Simple retrieval over short input | already good | similar | No — overkill |
| Multi-hop QA over millions of tokens | ~0% (won't fit) | 91% | Yes |
| Aggregation over hundreds of items | 44% | 57% | Yes |
| Pairwise comparison across items | 0.1% | 58% | Yes — only way |

### 3.2 Cost — median competitive, tail volatile

- On BrowseComp-Plus, RLM(GPT-5) costs roughly **$0.99 per task** at the median. Naive ingestion of the same 6–11M tokens would cost more *and* fail.
- **However:** 95th-percentile cost can be ~3× the median because some inputs trigger long recursive trajectories.
- Implication: cost is **probabilistic, not deterministic**. Budgets and caps must be designed in, not bolted on.

### 3.3 Latency — slower per request

- RLM is iterative: the model writes code, runs it, observes output, writes more code, and may dispatch many sub-calls. In the paper these run sequentially, so wall-clock is materially worse than a single LLM call.
- Async sub-calls are an obvious engineering improvement but are not done in the published work.
- Implication: not suitable for interactive chat replies. **Best for async / background / "ask and come back" UX.**

### 3.4 Reliability and quality variance

- The technique works zero-shot on frontier models (GPT-5, Qwen3-Coder-480B) but is sensitive to prompting; smaller models need fine-tuning.
- Some outputs hit formatting issues (final-answer tags) that the engineering team will need to handle defensively.
- Expect a v1 with rough edges, not a turn-key SLA.

### 3.5 Build vs. buy

- Open-source reference code exists (`rlms` package, `github.com/alexzhang13/rlm`). It's a research prototype, not a managed service.
- This is currently **engineering work, not vendor procurement** — no major provider sells RLM as a service yet. That can be either a moat or a maintenance tax depending on your situation.

---

## 4. What to Discuss with Engineering (6 min)

Bring these questions to the engineering conversation:

1. **Which currently-failing feature should we pilot first?** Pick something where today's answer is "we can't do that because context is too big" — that's where RLM has the largest delta.
2. **What's our latency budget for that feature?** RLM is async-friendly. If users tolerate a 30s–5min response, this is in scope. If we need sub-second, it isn't.
3. **What's our per-task cost cap?** Median is acceptable but the tail can spike. Agree on: hard cap, soft cap with warning, and behavior on overrun (truncate? fall back? alert?).
4. **Sandboxing.** RLM runs LLM-written code. We need a hardened execution environment, especially if the input contains untrusted content.
5. **Model strategy.** Pairing an expensive root model with a cheaper sub-call model controls cost. What's our default split?
6. **Observability.** Each request produces a trajectory of code + sub-calls. We should be able to inspect, replay, and audit them — important for trust and for debugging quality regressions.
7. **Eval harness.** Because quality is the main reason to adopt RLM, we need our own benchmark per feature; don't trust paper numbers as your SLA.
8. **Async sub-calls.** Listed as future work in the paper — for us, this is a near-term throughput unlock and should be on the implementation plan.

---

## 5. Roadmap Implications (4 min)

### 5.1 Features previously parked as "wait for bigger context windows" can move forward now
- Don't keep waiting for "GPT-6 with 50M context." RLM gets you most of the way today.

### 5.2 Plan for *long-running* features
- New UX patterns: progress indicators, partial-result streaming, "we'll email you when ready," background jobs.
- Notifications, queue management, retry policies become product-shaped questions.

### 5.3 Pricing and packaging
- Per-request cost is variable. Either: price per result (absorbing variance), tier the feature (free up to N tasks/month), or expose cost transparency.
- Quadratic tasks (pairwise) are the most expensive — package them as premium.

### 5.4 Quality story
- "We can now answer questions across your entire corpus, exhaustively" is a real differentiator. Marketing claim needs to be tied to our own eval scores, not the paper's.

### 5.5 Competitive read
- Whoever ships dense-long-context features first in a category gets a real moat — these features were not buildable 6 months ago.
- Conversely, foundation-model vendors will eventually bake something RLM-like into their own products. Plan a roadmap that wins in the next 12–18 months, not 5 years.

---

## 6. Q&A Prompts (2 min)

- Which one customer-blocking limitation maps cleanest onto "input too big or too dense"? That's our pilot.
- Are we willing to ship an async UX for it, or do we have to keep it synchronous (and therefore wait)?
- What's our policy on tail cost — fixed cap and degrade, or pay through and absorb?
- Do we have an internal eval set ready, or do we need to build one before we can claim quality?
- Do we want to be first-to-market with an RLM-powered feature in our category, or wait for a vendor to commoditize it?

---

## Key Takeaways

1. **RLM lets us promise things we couldn't promise before** — "ask anything about everything" features become real.
2. **Best fit:** async, content-heavy features where accuracy matters more than seconds of latency.
3. **Cost is competitive at the median, volatile at the tail.** Design budgets accordingly.
4. **It's not a product yet — it's a technique.** Engineering will build it on top of existing LLM APIs.
5. **First-mover advantage is real in the next 12–18 months**, before foundation-model vendors package this themselves.
