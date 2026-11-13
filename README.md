<!-- academy:title -->
# Building Applications on Language Models

بناء التطبيقات القائمة على النماذج اللغوية

AI Engineering Track · SDAIA Academy · AE-203 · Level 200

Build a tested bilingual assistant service on any language model: typed outputs, tools, grounded answers, evaluation and safety checks

Participants build a bilingual rider assistant for a fictional transit authority on top of any language model, hosted or open-weight. They call models through a provider-neutral interface, extract validated structured data from rider messages, add tool calls to a synthetic trip-status service, ground answers in a policy corpus with citations and abstention, write a small evaluation set and run the assistant against it, and add input and output checks for personal data and instruction-like text. The result is a small tested web service.

**Format:** Intensive: 4 teaching days of four sessions and a capstone day, with guided pre-work and a tracked follow-up task

**Course page:** https://sdaiaacademy.github.io/llm-applications/
<!-- /academy:title -->

## Outcomes

| | Outcomes | Level | Evidence |
|---|---|---|---|
| LO1 | Compare the main model API shapes and identify what changes in code when an application switches provider or moves to a local model, given the same request written for three interfaces | Awareness | an annotated comparison table that matches the reference on message structure, tool calls and usage reporting |
| LO2 | Implement structured extraction from free-text messages with schema validation, bounded retries and a fallback path, given 300 synthetic Arabic and English rider messages and a target schema | Applied | an extraction module with tests and a measured valid-output rate against a stated target |
| LO3 | Implement tool calling for two services with typed arguments, argument validation and handling of tool errors, given a synthetic trip-status service and a ticket-creation service | Applied | a passing test suite that includes malformed calls, timeouts and tool errors |
| LO4 | Implement a grounded answering step that retrieves policy passages, cites them and declines when the corpus holds no answer, given 120 bilingual policy pages and 30 questions the corpus cannot answer | Applied | answers whose citations are checked automatically and a measured abstention rate |
| LO5 | Prepare a small evaluation set and measure the assistant with code-based checks and one model-graded check validated against labels, given 40 labelled cases across extraction, tool use and grounded answers | Applied | an evaluation run with pass rates per category and the grader's agreement with the labels |
| LO6 | Configure input and output checks for personal data, off-topic requests and instruction-like text inside retrieved content, given 30 seeded risky messages and documents | Applied | a before-and-after table of blocked, masked and passed cases with false positives counted |
| LO7 | Build a bilingual assistant service that combines structured extraction, tool calls and grounded answers behind a tested API, given the case corpus and services, a provider-neutral client and a cost limit per 1,000 requests | Performance | a locally runnable service whose repository README reports evaluation results and cost from two measured runs |

<!-- academy:units -->
## Units

| Unit | Title | Sessions | Slides |
|---|---|---|---|
| Day 1 | Calling models well | Tokens, context and cost; Three API shapes, one interface; Prompts as versioned code; Streaming, timeouts and retries | [`slides/day1.html`](slides/day1.html) |
| Day 2 | Structured data and tools | Schemas for model output; Validation, retry and fallback; Tool calling; Workflow or agent | [`slides/day2.html`](slides/day2.html) |
| Day 3 | Grounded answers | Chunking and indexing a policy corpus; Lexical, dense and hybrid search; Answers with citations; Saying the answer is not there | [`slides/day3.html`](slides/day3.html) |
| Day 4 | Evaluate, protect and ship | A small evaluation set; One model grader, checked against labels; Input and output checks; Packaging the assistant as a service | [`slides/day4.html`](slides/day4.html) |
| Capstone | Capstone project presentations |  | [`slides/capstone.html`](slides/capstone.html) |
<!-- /academy:units -->

## Case study

**Darb Transit Authority** (هيئة درب للنقل العام) is a fictional city transport authority with four metro lines and eight bus routes, a trip-status service, a ticket service and 60 policies published in Arabic and English. Participants build **Wasil** (واصل), its rider assistant, one piece per lab: what a request costs, one client for hosted and local models, versioned instructions, retries, typed extraction from 300 rider messages, tool calls, grounded answers with citations and abstention, an evaluation set with a validated grader, input and output checks, and a tested web service.

All data is synthetic and generated with a fixed seed by `labs/prepare_data.py`: the messages carry fake names, phone numbers and identity numbers so that masking can be practised, one policy page is superseded, and one carries a planted instruction for "automated assistants". `labs/README.md` lists every file.

<!-- academy:labs -->
## Labs

Every lab is a notebook in `labs/`. Open it in Google Colab from the course page, or run it locally with `uv`. Exercises raise `NotImplementedError` until they are done; the reference versions are in `labs/solutions/`.

| | Session | Lab | File |
|---|---|---|---|
| 1.1 | Day 1 · Session 1 | Tokens and cost for 10,000 messages | [`D1_1_tokens_cost.ipynb`](labs/D1_1_tokens_cost.ipynb) |
| 1.2 | Day 1 · Session 2 | One request, three shapes, one client | [`D1_2_three_shapes.ipynb`](labs/D1_2_three_shapes.ipynb) |
| 1.3 | Day 1 · Session 3 | Wasil's instructions as a versioned template | [`D1_3_prompt_versions.ipynb`](labs/D1_3_prompt_versions.ipynb) |
| 1.4 | Day 1 · Session 4 | Timeouts, retries and a fallback model | [`D1_4_retries.ipynb`](labs/D1_4_retries.ipynb) |
| 2.1 | Day 2 · Session 1 | Route, date and complaint type as a typed object | [`D2_1_schemas.ipynb`](labs/D2_1_schemas.ipynb) |
| 2.2 | Day 2 · Session 2 | Repair, cap and a human queue | [`D2_2_repair_fallback.ipynb`](labs/D2_2_repair_fallback.ipynb) |
| 2.3 | Day 2 · Session 3 | The trip-status service as a tool | [`D2_3_tool_calling.ipynb`](labs/D2_3_tool_calling.ipynb) |
| 2.4 | Day 2 · Session 4 | Workflow or tool loop | [`D2_4_workflow_agent.ipynb`](labs/D2_4_workflow_agent.ipynb) |
| 3.1 | Day 3 · Session 1 | Two chunkings of the policy corpus | [`D3_1_chunking.ipynb`](labs/D3_1_chunking.ipynb) |
| 3.2 | Day 3 · Session 2 | Keyword, vector and hybrid search | [`D3_2_search.ipynb`](labs/D3_2_search.ipynb) |
| 3.3 | Day 3 · Session 3 | Answers with checked citations | [`D3_3_citations.ipynb`](labs/D3_3_citations.ipynb) |
| 3.4 | Day 3 · Session 4 | Saying the answer is not there | [`D3_4_abstention.ipynb`](labs/D3_4_abstention.ipynb) |
| 4.1 | Day 4 · Session 1 | Forty golden cases | [`D4_1_eval_set.ipynb`](labs/D4_1_eval_set.ipynb) |
| 4.2 | Day 4 · Session 2 | A faithfulness grader against labels | [`D4_2_grader.ipynb`](labs/D4_2_grader.ipynb) |
| 4.3 | Day 4 · Session 3 | Masking and flagging | [`D4_3_safety_checks.ipynb`](labs/D4_3_safety_checks.ipynb) |
| 4.4 | Day 4 · Session 4 | Wasil as a tested web service | [`D4_4_service.ipynb`](labs/D4_4_service.ipynb) |
<!-- /academy:labs -->

## Capstone

An assistant for one of three supplied cases or an approved own case, submitted as a public repository with tests, an evaluation set of at least 40 cases and a README that reports results from two measured runs, cost per 1,000 requests and known limits, followed by an eight-minute defence and four minutes of questions

**Submission:** a public GitHub repository with the service, its tests, an evaluation set of at least 40 cases with its run logs and commit history, and a README that reports results from two measured runs, cost per 1,000 requests and known limits. Then an eight-minute defence with four minutes of questions: the participant runs the evaluation, explains a failing case the assessor selects, and predicts the result of one new case the assessor adds.

The three supplied cases, all on the Darb data, and the starter are in `labs/capstone/`. Rubric: working service and tests 25, structured output and tools 20, grounding and abstention 20, evaluation 20, safety checks and limits 15.

## Prerequisites

- FN-101 Python for Data and AI Work
- FN-102 Command Line, Git and Reproducible Projects
- FN-105 How Machine Learning and Language Models Work
- Calls a web API from Python and handles JSON
- Writes and runs unit tests

<!-- academy:tools -->
## Tools

Each line is a capability; the examples are interchangeable.

- **Language model access:** a free hosted open-weight model, a locally served open-weight model, any commercial API
- **Provider-neutral client or gateway:** LiteLLM, an OpenAI-compatible local server such as llama.cpp server or Ollama
- **Schema validation and structured output:** Pydantic, Instructor, Outlines
- **Embeddings and vector search:** Sentence Transformers with FAISS, pgvector, Chroma
- **Lexical search:** SQLite full-text search, rank-bm25
- **Personal data detection:** Presidio, regular-expression and dictionary rules
- **Web service framework:** FastAPI, Flask
- **Evaluation harness:** pytest with custom assertions, promptfoo, Inspect
<!-- /academy:tools -->

<!-- academy:sources -->
## Sources

### Model APIs and clients

- [OpenRouter: API rate limits](https://openrouter.ai/docs/api-reference/limits)
- [OpenRouter: models](https://openrouter.ai/models)
- [OpenRouter: structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [OpenAI API reference: Chat Completions](https://developers.openai.com/api/reference/resources/chat)
- [OpenAI API reference: Responses](https://developers.openai.com/api/reference/resources/responses)
- [Anthropic API reference: Messages](https://docs.anthropic.com/en/api/messages)
- [Open Responses specification](https://www.openresponses.org/)
- [OpenAI Python library](https://github.com/openai/openai-python)
- [LiteLLM documentation](https://docs.litellm.ai/docs/)
- [Ollama: OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [Qwen3 open tokenizer (model card)](https://huggingface.co/Qwen/Qwen3-0.6B)
- [Model Context Protocol](https://modelcontextprotocol.io/)

### Libraries used in the labs

- [Pydantic: JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/)
- [rank-bm25](https://github.com/dorianbrown/rank_bm25)
- [SQLite FTS5 full-text search](https://www.sqlite.org/fts5.html)
- [Python sqlite3](https://docs.python.org/3/library/sqlite3.html)
- [FastAPI: testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Microsoft Presidio](https://github.com/microsoft/presidio)
- [promptfoo](https://www.promptfoo.dev/)
- [Inspect](https://inspect.aisi.org.uk/)

### National references

- [Personal Data Protection Law](https://sdaia.gov.sa/en/SDAIA/about/Documents/PersonalDataProtectionLaw.pdf)
- [Data Classification Policy (National Data Management Office)](https://sdaia.gov.sa/en/SDAIA/about/Documents/DataClassificationPolicy.pdf)
- [Generative AI Guideline for Government](https://sdaia.gov.sa/en/SDAIA/about/Files/GenAIGuidelinesForGovernmentENCompressed.pdf)
- [Generative AI Guideline for Public](https://sdaia.gov.sa/en/SDAIA/about/Files/GenerativeAIPublicEN.pdf)
- [Principles of AI Ethics](https://sdaia.gov.sa/en/SDAIA/about/Documents/ai-principles.pdf)
<!-- /academy:sources -->

### National references

- Personal Data Protection Law and its implementing regulations: https://sdaia.gov.sa/en/SDAIA/about/Documents/PersonalDataProtectionLaw.pdf
- NDMO Data Classification Policy: https://sdaia.gov.sa/en/SDAIA/about/Documents/DataClassificationPolicy.pdf
- SDAIA Generative AI Guidelines: https://sdaia.gov.sa/en/SDAIA/about/Files/GenAIGuidelinesForGovernmentENCompressed.pdf (for government) and https://sdaia.gov.sa/en/SDAIA/about/Files/GenerativeAIPublicEN.pdf (for the public)
- SDAIA AI Ethics Principles: https://sdaia.gov.sa/en/SDAIA/about/Documents/ai-principles.pdf
