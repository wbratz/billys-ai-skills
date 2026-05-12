# Director To C-Level: Recursive Language Models

## Executive Thesis

Recursive Language Models are a way to make AI systems work over much larger and denser bodies of information than normal prompting allows. Instead of pushing all information into a model's context window, an RLM places the information in an external environment and lets the model inspect, transform, delegate, and aggregate results recursively.

Why executives should care: this is a credible path to using AI on enterprise-scale knowledge work where the relevant context lives across codebases, documents, tickets, logs, customer conversations, policies, and research. It can improve quality on complex long-context tasks, but it needs governance around cost, security, and auditability.

## 30-Minute Agenda

0:00-0:05 - Business problem

- Important enterprise questions rarely fit in one clean prompt.
- Current approaches often rely on search, retrieval, or summarization.
- Those approaches can miss details, lose context, or fail when the answer requires dense reasoning across many sources.

0:05-0:10 - What RLM does

- RLM is an inference-time architecture around a language model.
- It stores the long input outside the model, usually in an executable environment.
- The model writes code to inspect and process the context.
- It can launch recursive sub-model calls on selected slices.
- It builds intermediate results and final outputs in variables, giving it a larger effective working space.

0:10-0:16 - Evidence from the paper

- The paper reports that RLMs handle inputs into the 10M+ token regime.
- RLM(GPT-5) outperformed direct GPT-5 and common long-context scaffolds across evaluated tasks.
- On BrowseComp-Plus with 6M-11M-token inputs, RLM(GPT-5) scored 91.3, compared with 70.5 for the summary-agent baseline and 51.0 for CodeAct with BM25.
- On CodeQA, RLM(GPT-5) scored 62.0 compared with 24.0 for base GPT-5.
- On OOLONG-Pairs, base GPT-5 was effectively unable to solve the task, while RLM(GPT-5) reached 58.0 F1.
- Costs were often comparable at the median, but outlier RLM runs can be significantly more expensive because task trajectories vary.

0:16-0:22 - Why this matters to us

RLM is relevant anywhere we want AI to operate over large proprietary context:

- Engineering: repo-wide analysis, architecture understanding, migration planning, incident reconstruction.
- Product: customer feedback synthesis, PRD gap analysis, roadmap evidence gathering.
- Operations: policy comparison, compliance evidence, root-cause analysis.
- Support and success: long account history synthesis and escalation analysis.
- Research and strategy: multi-document market, competitor, or technical analysis.

The strategic value is not just larger context. It is better decomposition and more auditable work on complex questions.

0:22-0:26 - Governance and risk

Key risks:

- Cost variance: some runs may be cheap, while difficult runs can launch many subcalls.
- Latency variance: recursive workflows can be slower than one model call.
- Security: REPL execution needs sandboxing and permission boundaries.
- Data governance: source access must respect customer, employee, and regulated-data constraints.
- Reliability: model-specific behavior, brittle final-answer protocols, and hallucinated synthesis still require review.
- Evaluation: the paper itself says implementation mechanisms and natural long-context evaluations remain under-explored.

Controls:

- Start internal only.
- Require source evidence in outputs.
- Set budget, timeout, recursion, and subcall limits.
- Log trajectories and costs.
- Run in a sandboxed environment.
- Compare against existing baselines before scaling.

0:26-0:30 - Recommended action

Launch one 30-60 day internal pilot with a measurable business workflow:

- Candidate 1: engineering incident and codebase analysis.
- Candidate 2: product feedback and roadmap evidence synthesis.
- Candidate 3: compliance or policy evidence extraction.

Pilot success criteria:

- Better expert-review score than current workflow.
- Clear reduction in manual analysis time.
- Acceptable cost per reviewed answer.
- Evidence traceability for every major claim.
- No sensitive data leakage or unsafe execution path.

## Executive Talking Points

- "RLM is a way to make AI reason over large enterprise context without forcing all of it into the model window."
- "The benefit is strongest when the answer depends on many details across a large corpus."
- "This should start as an internal decision-support capability, not an autonomous production decision-maker."
- "The governance model is clear: sandbox execution, budget limits, source evidence, audit logs, and human review."
- "The upside is better use of our proprietary knowledge base: code, tickets, docs, customer feedback, logs, and prior decisions."

## Decision Request

Approve a bounded internal pilot with engineering ownership and product participation.

Recommended pilot design:

- Duration: 30-60 days.
- Scope: one high-context workflow with available ground truth or expert review.
- Budget: fixed per-run and total pilot cap.
- Security: sandboxed execution and restricted source access.
- Review: weekly findings with examples, cost, latency, and failure modes.

## Bottom Line

RLM is worth caring about because it changes the AI scaling question from "how much can fit in the prompt?" to "how intelligently can the model inspect and reason over the information we already have?" That is directly relevant to enterprise AI adoption, especially for engineering, product, support, operations, and strategy workflows.
