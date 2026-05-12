# Product Owners: Recursive Language Models

## Audience And Outcome

Audience: product owners and product managers who work closely with engineering.

Outcome: product should understand what RLM can unlock, how to recognize good use cases, what tradeoffs to ask engineering about, and how to define pilot success.

## 30-Minute Agenda

0:00-0:04 - The product problem

- Many product and engineering decisions depend on large bodies of context: customer calls, tickets, specs, research, logs, design docs, code, and prior decisions.
- Today we often ask an AI tool to summarize, search, or ingest as much context as possible.
- That breaks down when the answer depends on many details spread across the full corpus.

0:04-0:09 - RLM in plain English

- RLM stands for Recursive Language Model.
- Instead of stuffing all the material into a chat prompt, the system gives the model controlled access to the material in an external workspace.
- The model can inspect pieces, ask subquestions, compare results, and build an answer step by step.
- Think of it as an AI analyst that can read a giant evidence room with a notebook and helpers, rather than a chatbot reading one oversized document.

0:09-0:15 - Why product should care

- Better answers on dense, messy context: RLM is designed for cases where details matter across the whole corpus.
- Less dependence on lossy summaries: summaries can drop the detail needed for a later decision.
- More auditable work: engineering can log which chunks, subcalls, and evidence were used.
- Potentially better economics than repeatedly feeding entire corpora into a model, though long runs can be expensive.
- Useful for product discovery and delivery work where the source material is too large for normal review.

0:15-0:21 - Product-owner use cases

Strong candidates:

- Analyze hundreds or thousands of customer feedback items for themes, edge cases, contradictions, and supporting quotes.
- Compare a PRD against design docs, API docs, and implementation notes to identify gaps.
- Summarize long research corpora into actionable product bets with evidence.
- Turn incident reports and support logs into product-quality root-cause and customer-impact narratives.
- Ask "what would break if we changed this behavior?" across code, docs, and tickets.
- Find repeated unmet customer needs across sales notes, support cases, and roadmap docs.

Weak candidates:

- One-off content generation.
- Simple document search.
- Fast interactive chat where latency matters more than depth.
- Tasks where a concise manual summary is already enough.
- Any customer-facing autonomous decision without review.

0:21-0:25 - Questions product should ask engineering

- What evidence will the system return with the answer?
- What source systems will it read, and what should be excluded?
- What is the expected latency and tail latency?
- What is the cost budget per run and per pilot?
- How will we know it is better than search, RAG, or a normal model call?
- Can we replay or audit the model's steps?
- What human approval is required before using the output?
- How do we handle sensitive customer or company data?

0:25-0:28 - Success metrics

Product quality:

- More complete issue/theme discovery.
- Fewer missed requirements and edge cases.
- Higher agreement between AI findings and expert human review.
- Better traceability from recommendation to source evidence.

Operational metrics:

- Time saved per analysis.
- Reduction in manual document reading.
- Cost per accepted insight.
- Latency per run and tail-latency frequency.
- Rate of hallucinated, unsupported, or stale claims.

0:28-0:30 - Discussion prompts

- Which product rituals involve too much context for humans or chat tools?
- Where do summaries currently lose important details?
- Which teams can provide a gold-standard review set for evaluation?
- Which pilot would matter if it improved accuracy by 20 percent?

## Speaker Notes

The product value is not "more AI." It is better work on large, messy evidence sets. RLM matters when the system needs to inspect a lot of material, keep intermediate findings, and combine them into a final answer.

For product owners, the main operating principle is to frame RLM pilots as decision-support workflows, not magic automation. The best first pilots produce recommendations with evidence that a human can review.

The paper's strongest practical message is that simple context expansion is not enough. As tasks become more complex, performance drops even inside model context windows. RLM tries to solve that by changing the workflow: inspect, decompose, recurse, aggregate, verify.

## Product Pilot Recommendation

Pilot: customer feedback plus support-ticket synthesis for one active roadmap area.

Inputs:

- Customer feedback exports.
- Support tickets.
- Sales notes.
- Existing PRD.
- Known bugs and feature requests.

Outputs:

- Top customer pain points with source evidence.
- Contradictions or segmentation differences.
- Feature opportunities and non-goals.
- Engineering questions and risks.
- Candidate success metrics.

Review:

- Product, engineering, support, and design review the output.
- Score evidence quality, completeness, novelty, and actionability.

## Takeaways

- RLM is most useful where product work is blocked by too much relevant context.
- Product should demand evidence, auditability, cost limits, and clear comparison against simpler approaches.
- The first adoption step should be a bounded internal pilot tied to a real roadmap decision.
