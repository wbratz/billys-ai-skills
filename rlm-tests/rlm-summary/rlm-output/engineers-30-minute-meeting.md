# Engineers: Recursive Language Models

## Audience And Outcome

Audience: engineers building AI-assisted coding, research, analysis, data, or agent workflows.

Outcome: engineers should leave knowing what an RLM is, how it differs from long-context prompting, when it is worth using, and what to evaluate before adopting it in our stack.

## 30-Minute Agenda

0:00-0:03 - Frame the problem

- LLMs degrade on long inputs even before hitting hard context limits.
- The paper calls this "context rot": quality falls as prompts get longer and tasks get denser.
- The core engineering question: should we put everything in the prompt, retrieve a few chunks, summarize, or let the model operate over the context as an external object?

0:03-0:08 - What RLM is

- A Recursive Language Model is an inference-time scaffold around a base language model.
- The full prompt or corpus is placed in an external environment, such as a Python REPL, as a variable.
- The root model sees metadata and instructions, then writes code to inspect, slice, transform, and query parts of the context.
- The model can invoke sub-model calls on programmatically selected snippets, store intermediate results in variables, and return a final answer from the environment.

0:08-0:14 - Why the design matters

- It gives the model a symbolic handle to long input instead of forcing the entire input through the neural context window.
- It enables programmatic decomposition, such as loops over chunks, regex filtering, aggregation, and verification.
- It supports long outputs by building variables in the REPL, rather than requiring one autoregressive response to contain everything.
- It differs from normal tool-use agents because recursive calls can be launched programmatically inside code, not only manually described in a short action list.

0:14-0:20 - What the paper found

- The paper evaluates RLMs on CodeQA, BrowseComp-Plus, OOLONG, and OOLONG-Pairs.
- GPT-5 as a base model scores 24.0 on CodeQA, while RLM(GPT-5) scores 62.0.
- On BrowseComp-Plus with 6M-11M-token inputs, RLM(GPT-5) scores 91.3, while the summary-agent baseline scores 70.5 and CodeAct with BM25 scores 51.0.
- On OOLONG-Pairs, base GPT-5 is effectively at 0.1 F1, while RLM(GPT-5) reaches 58.0.
- Costs are usually comparable at the median, but tail runs can be much more expensive because trajectories vary in length.

0:20-0:25 - When engineers should use it

Use RLM when:

- The input is larger than the model window, or close enough that context quality is unreliable.
- The task needs dense access across many parts of the context, not just one retrieved snippet.
- The task benefits from programmatic inspection, aggregation, filtering, or verification.
- You need long, structured outputs assembled from many partial results.
- Examples: large codebase QA, multi-document research, incident timeline reconstruction, compliance evidence extraction, repo-wide migration analysis, long customer feedback synthesis.

Do not use RLM when:

- The prompt is small enough for a normal model call.
- A simple retrieval query gives the answer.
- Low latency is more important than depth.
- The output must be deterministic without human review.
- The environment cannot safely sandbox generated code.

0:25-0:28 - Engineering adoption checklist

- Context loading: define loaders for files, URLs, PDFs, logs, tickets, and code.
- Chunking: tune chunk size and overlap by task, not just token count.
- Execution environment: prefer sandboxed or subprocess execution. Avoid unrestricted local execution for untrusted context.
- Model routing: use a strong root model and cheaper subcall models where quality allows.
- Budgets: set max depth, max iterations, timeout, token/cost budgets, and subcall caps.
- Observability: log chunk plans, subcalls, intermediate variables, final evidence, errors, and costs.
- Evaluation: compare against direct prompting, RAG, summarization, and hand-built pipelines.
- Safety: treat prompt injection and generated code execution as first-class risks.

0:28-0:30 - Discussion prompts

- Which current workflows fail because context is too large or too dense?
- Which tasks need dense corpus access rather than retrieval?
- What sandbox should generated code run in?
- What should count as success: accuracy, review time saved, cost, latency, or evidence quality?

## Speaker Notes

The key engineering shift is moving context out of the model window and into an environment. The model uses code as a control surface over the context, then recursively asks smaller questions over selected slices. This is closer to an agentic map/reduce system than a bigger prompt.

RLM is not just "RAG with a loop." RAG chooses snippets to put back into the context window. RLM keeps the corpus outside the window and lets the model use code, loops, variables, and subcalls to decide how much of the corpus to inspect.

The major implementation risks are not mysterious: cost variance, runtime variance, model-specific behavior, brittle final-answer protocols, and code execution security. The paper explicitly notes synchronous calls were slow and that async subcalls plus sandboxed REPLs are important future directions.

## Practical Pilot Recommendation

Start with an internal, non-customer-facing workflow where correctness can be judged:

- Repo-wide "explain this subsystem" analysis.
- Long incident or support-thread timeline synthesis.
- Multi-document design review.
- Migration impact analysis across code, docs, and tickets.

Benchmark against current workflow plus direct model and RAG baselines. Require evidence links or source chunk IDs in every answer.

## Takeaways

- RLM is an inference scaffold, not a new base model requirement.
- It is useful when context size and task complexity make normal prompting unreliable.
- It trades simpler prompting for better decomposition, stronger long-context behavior, and more operational controls.
- We should pilot it behind clear budgets, sandboxing, and evals before putting it in production workflows.
