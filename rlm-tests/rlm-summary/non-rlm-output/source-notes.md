# Source Notes: Recursive Language Models

Paper: "Recursive Language Models" by Alex L. Zhang, Tim Kraska, and Omar Khattab.
arXiv:2512.24601v2, posted January 28, 2026.
URL: https://arxiv.org/html/2512.24601v2

## Core Claim

Recursive Language Models, or RLMs, are an inference-time pattern for letting an LLM work over prompts and corpora far larger than its native context window. The paper frames RLM as a scaffold around a base model, not necessarily a new model architecture. The key move is to treat the long prompt as data in an external environment, usually a REPL, instead of stuffing the entire prompt into the model context.

The root model receives metadata about the input and can write code to inspect, transform, chunk, search, and aggregate the input. It can also call sub-LLMs on programmatically selected snippets. Intermediate results live in variables, not in the model's context window, and the final answer is returned from the environment.

## Why This Is Different From Normal Long Context

The paper argues that simply increasing context length is not enough because model quality degrades as prompts get longer, especially when the task requires dense reasoning across many parts of the input. The authors call out context compaction and summarization as useful but limited: summarization assumes that earlier details can be safely compressed or forgotten, which breaks down when the answer depends on many details across the whole input.

RLM changes the operating model:

- The full input becomes an external object with a symbolic handle.
- The model writes code to inspect and manipulate that object.
- The model can launch recursive sub-calls inside loops over selected chunks.
- The model stores intermediate state outside the context window.
- The model can construct outputs longer than what a single autoregressive response would comfortably support.

## Three Design Requirements

The paper emphasizes three design choices that make RLM more expressive than ordinary tool agents:

1. Give the model a symbolic handle to the whole prompt.
2. Let the model build final outputs in external state rather than only generating a final text response directly.
3. Allow symbolic recursion: code in the environment must be able to invoke sub-model calls programmatically, including inside loops.

## Evidence From The Paper

The evaluation covers long-context tasks with different complexity profiles:

- S-NIAH: simple needle-in-a-haystack retrieval where the relevant information is small.
- BrowseComp-Plus: multi-hop research over 1,000 documents and 6M to 11M token inputs.
- OOLONG: dense aggregation where the model must use nearly all entries.
- OOLONG-Pairs: pairwise dense reasoning where the number of relationships can scale quadratically.
- CodeQA: repository understanding over codebases up to millions of tokens.

Notable reported results:

- RLMs processed inputs in the 10M+ token range.
- RLM(GPT-5) reached 91.3% on BrowseComp-Plus, compared with 70.5% for a summary agent and 51.0% for a CodeAct + BM25 baseline. The base GPT-5 call could not fit the task.
- On OOLONG-Pairs, RLM(GPT-5) reached 58.0 F1, while base GPT-5 was effectively at 0.1 and the summary agent was also effectively at 0.1.
- On CodeQA, RLM(GPT-5) reached 62.0, above the base GPT-5 result of 24.0 and the summary agent result of 58.0.
- RLMs had comparable median API costs in several settings, but the paper also reports high variance and long-tail cost outliers.
- A small Qwen3-8B model improved after fine-tuning on 1,000 RLM trajectory samples, suggesting that native RLM behavior can be trained.

## Practical Limitations

The paper is clear that RLM is not a free win:

- Base models can outperform RLM on small inputs, so there is a tradeoff point.
- RLM trajectories can be slow when sub-calls are blocking or sequential.
- Costs can spike when the model overuses recursive calls.
- Models need enough coding and tool-use ability to operate effectively in a REPL.
- Prompting is model-sensitive; the same RLM prompt did not work equally well across evaluated models.
- Distinguishing final answers from intermediate reasoning can be brittle without model and scaffold support.

## Practical Interpretation

RLM should be treated as a high-context workflow architecture. It is most attractive when the task has one or more of these properties:

- The input is too large for the model context window.
- The answer requires dense use of many input items, not just finding one passage.
- Summarization would lose important details.
- The workflow benefits from intermediate artifacts, traceability, and staged aggregation.
- The user can tolerate asynchronous execution or longer latency for higher answer quality.

It is less attractive for short prompts, simple retrieval, low-latency chat, or tasks where a standard RAG pipeline already gives strong, auditable answers.
