# Product Meeting — Recursive Language Models (RLM)

**Duration:** 30 minutes
**Audience:** Product owners working alongside engineering
**Source:** Zhang, Kraska, Khattab — *Recursive Language Models* (arXiv:2512.24601v2, ICML 2026)

---

## Agenda (30 min)

| Time | Topic |
|---|---|
| 0:00–0:04 | Why this is on our radar |
| 0:04–0:12 | What RLM unlocks — capabilities, in product terms |
| 0:12–0:19 | Tradeoffs: cost, latency, reliability |
| 0:19–0:24 | Product opportunities to put on the backlog |
| 0:24–0:30 | What to ask engineering this quarter + Q&A |

---

## 1. Why this is on our radar (4 min)

Today, the answer to "can we build a feature that reads all of X?" is usually **"only if X fits in the model's window."** That single constraint silently kills a long list of features: search-the-whole-archive, summarize-this-entire-account, audit-every-call-recording, answer-from-our-full-docs.

RLM is a research-validated pattern (paper at ICML 2026) that changes that constraint. Instead of fitting the data into the model, the model **operates on the data through code** — slicing, filtering, fanning out cheap reads — and only the conclusions enter the model's brain. Result: models can usefully process inputs **up to ~100× larger than their context window**, often at lower cost than direct use.

This is not a vendor announcement. It's a technique any team can adopt; the reference code is open source.

---

## 2. What RLM unlocks (8 min)

Concrete capabilities the paper demonstrates:

- **Cross-document reasoning at scale.** On BrowseComp-Plus (a 1,000-document research-style task), base GPT-5 scored **0%** (it couldn't even fit the input); GPT-5 with RLM scored **91.3%**. That's the jump from "feature impossible" to "feature ships."
- **Higher accuracy on long inputs.** On OOLONG (long-context QA), GPT-5 + RLM beats base GPT-5 **56.5% vs. 44.0%**. That's the difference between "users trust the answer" and "users stop using the feature."
- **Open models can compete.** A fine-tuned **8B-parameter** open-source model with RLM approaches GPT-5 quality on three long-context tasks. Translation: privacy-sensitive deployments (on-prem, regulated industries) become viable for long-context features.
- **Code-aware analysis.** CodeQA accuracy moves from 24% → 62% with RLM. Anything where the input is a repo, schema dump, or large config benefits.

**Product translation — features that move from "no" to "yes":**
- "Summarize my last 12 months of activity across all surfaces."
- "Search across every PDF in my workspace and answer this."
- "Review this entire codebase / contract / case file."
- "Pull the trend out of these 50,000 support tickets."
- "Audit this 8-hour call recording for compliance issues."

---

## 3. Tradeoffs (7 min)

Three numbers to keep in mind:

**Cost.** Per-task cost on the paper's benchmark: **$0.99 average** for GPT-5 + RLM vs. $1.50–$2.75 extrapolated for direct ingestion. So roughly **30–60% cheaper on average**. But: **outlier runs can be more expensive** because the model sometimes loops. We will need budget caps per task.

**Latency.** The current reference implementation runs sub-tasks **sequentially**, so a complex query can take tens of seconds. Async fan-out is straightforward but adds engineering work. **Implication:** RLM is great for async/batch UX (background jobs, "we'll email you the report"), risky for synchronous chat-style features where users expect <2s responses.

**Reliability.** Higher variance than a plain model call. The paper flags:
- Occasional brittle termination (model returns a plan instead of an answer).
- Token exhaustion on hard tasks.
- Smaller models can't drive the loop well without fine-tuning.

**Implication:** RLM features need evaluation harnesses, retries, and an "I don't know" fallback path. Treat them like any system with non-trivial failure modes — not like a magic black box.

---

## 4. Product opportunities for the backlog (5 min)

Rank candidates by **(value of long context) × (tolerance for async latency)**:

| Idea | Why it fits RLM |
|---|---|
| "Account intelligence" digest across all customer touchpoints | Long, sparse, async — perfect fit |
| Repo-wide code review / "explain this codebase" | Large input, code-heavy (RLM strong here) |
| Compliance / legal pass over every contract or recording | Huge input, async by nature, accuracy critical |
| Migration assistants over entire docs sets | One-time per customer, latency tolerant |
| Multi-document research tools for internal users (support, sales, eng) | Cross-doc reasoning is the whole point |

What we **shouldn't** rush into RLM:
- Sub-second chat features over short inputs (no benefit, adds variance).
- Anything where the user can't tolerate "no answer / try again" outcomes without a strong eval suite in place.

---

## 5. What to ask engineering this quarter (4 min) + Q&A

Conversation starters with eng:

1. **"Which features did we deprioritize because input didn't fit?"** Build the list. It's our RLM backlog.
2. **"What's our provider mix?"** Closed APIs with expensive sub-calls eat the savings. Cheap fast models (Haiku, Flash, open models) maximize them.
3. **"What's our eval setup look like for long-context tasks?"** If we don't have one, that's the first investment — RLM features without evals will regress silently.
4. **"Async or sync?"** Push for async-first UX on early RLM features. Sync comes later when patterns are proven.
5. **"Open-source 8B + fine-tuning?"** For privacy-sensitive products, this could be a competitive moat.

**Q&A prompts:**
- Where are we losing deals or NPS because "AI can't read the full thing"?
- What's our budget per AI task today? Could we afford $1–$2 per task for a flagship long-context feature?
- Which features can move to async without hurting UX?
- Should we run an internal RLM pilot in Q3 — and if so, on which workflow?

---

## Key takeaways

1. **RLM is not a new model — it's a new way to use the models we already have.** No vendor lock-in required.
2. The headline win is **"features that were impossible become possible"** — especially anything that needs to reason across documents, recordings, or codebases too big to fit in one prompt.
3. **Cost is roughly flat or favorable**; latency is the real tradeoff today. Plan for async UX.
4. **Eval discipline matters more than usual.** RLM features fail in subtler ways than direct model calls.
5. We should leave this meeting with **one shortlisted feature** to spike with engineering in the next sprint.
