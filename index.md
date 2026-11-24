---
course: "Building Applications on Language Models"
code: "AE-203"
version: "2027.2.0"
language: "en"
view: "trainee"
source: "https://sdaiaacademy.github.io/ae-203/index.html"
---

# Building Applications on Language Models

بناء التطبيقات القائمة على النماذج اللغوية

AI Engineering Track · 4 teaching days + capstone day · 26 hours · Level 200

Build a tested bilingual assistant service on any language model: typed outputs, tools, grounded answers, evaluation and safety checks

Participants build a bilingual rider assistant for a fictional transit authority on top of any language model, hosted or open-weight. They call models through a provider-neutral interface, extract validated structured data from rider messages, add tool calls to a synthetic trip-status service, ground answers in a policy corpus with citations and abstention, write a small evaluation set and run the assistant against it, and add input and output checks for personal data and instruction-like text. The result is a small tested web service.

**Who it is for:** Practitioners. Graduates and early-career developers who have completed the FN courses or passed the placement test, and software engineers moving into AI work.

**Format:** Intensive: 4 teaching days of four sessions and a capstone day, with guided pre-work and a tracked follow-up task

## The case study

**Darb Transit Authority.** Darb Transit Authority is a fictional city transport authority with four metro lines and eight bus routes. Participants build Wasil, its bilingual rider assistant: token and cost estimates, one client for hosted and local models, versioned instructions, retries, typed extraction from 300 rider messages in Arabic, English and Arabizi, tool calls to a trip-status and a ticket service, grounded answers with citations and abstention over 120 policy pages, a 40-case evaluation set with a validated model grader, personal data masking and instruction detection, and a tested web service. All data is synthetic and generated with a fixed seed.

## The course

### Day 1: Calling models well

Slides: https://sdaiaacademy.github.io/ae-203/slides/day1.md

- **Session 1: Tokens, context and cost**
  - Count the tokens of a request, its instructions and its tool definitions
  - Compare the token cost of the same text in Arabic and English
  - Estimate daily cost and latency from tokens and example prices
  - [Lab 1.1: Tokens and cost for 10,000 messages (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D1_1_tokens_cost.ipynb)
- **Session 2: Three API shapes, one interface**
  - Locate messages, tool calls and usage in each of the three API shapes
  - Fill a comparison table that matches the reference
  - Switch between a hosted and a local endpoint by configuration
  - [Lab 1.2: One request, three shapes, one client (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D1_2_three_shapes.ipynb)
- **Session 3: Prompts as versioned code**
  - Separate system instructions from the rider's message
  - Keep a prompt as a versioned template with an owner
  - Pin a prompt's behaviour with tests before a release
  - [Lab 1.3: Wasil's instructions as a versioned template (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D1_3_prompt_versions.ipynb)
- **Session 4: Streaming, timeouts and retries**
  - Measure the time to first token of a streamed reply
  - Retry only the errors worth retrying, with backoff
  - Fall back to a second model and test every path
  - [Lab 1.4: Timeouts, retries and a fallback model (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D1_4_retries.ipynb)

### Day 2: Structured data and tools

Slides: https://sdaiaacademy.github.io/ae-203/slides/day2.md

- **Session 1: Schemas for model output**
  - Write a schema whose constraints catch wrong values
  - Request output under a JSON Schema response format
  - Measure the valid-output rate on a sample of messages
  - [Lab 2.1: Route, date and complaint type as a typed object (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D2_1_schemas.ipynb)
- **Session 2: Validation, retry and fallback**
  - Turn a validation error into a repair message
  - Cap the retries of a repair loop
  - Route failures to a human queue and measure against a target
  - [Lab 2.2: Repair, cap and a human queue (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D2_2_repair_fallback.ipynb)
- **Session 3: Tool calling**
  - Define a tool from a typed argument model
  - Validate arguments and return errors the model can act on
  - Test correct calls, malformed calls, tool errors and timeouts
  - [Lab 2.3: The trip-status service as a tool (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D2_3_tool_calling.ipynb)
- **Session 4: Workflow or agent**
  - Write a task as a fixed workflow of model and tool steps
  - Write the same task as a model-driven tool loop
  - Choose between them from measured steps, cost and failures
  - [Lab 2.4: Workflow or tool loop (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D2_4_workflow_agent.ipynb)

### Day 3: Grounded answers

Slides: https://sdaiaacademy.github.io/ae-203/slides/day3.md

- **Session 1: Chunking and indexing a policy corpus**
  - Normalise Arabic text before indexing
  - Chunk pages by section and by fixed windows
  - Index chunks in SQLite full-text search and query them
  - [Lab 3.1: Two chunkings of the policy corpus (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D3_1_chunking.ipynb)
- **Session 2: Lexical, dense and hybrid search**
  - Measure search with hit at k and mean reciprocal rank
  - Compare keyword and vector search by language
  - Fuse two rankings with reciprocal rank fusion
  - [Lab 3.2: Keyword, vector and hybrid search (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D3_2_search.ipynb)
- **Session 3: Answers with citations**
  - Give the model passages with stable identifiers
  - Check by code that each citation exists and supports the answer
  - Keep superseded pages from being cited
  - [Lab 3.3: Answers with checked citations (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D3_3_citations.ipynb)
- **Session 4: Saying the answer is not there**
  - Set an abstention threshold from measured scores
  - Measure abstention and false abstention rates
  - Tell the rider plainly and offer a person
  - [Lab 3.4: Saying the answer is not there (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D3_4_abstention.ipynb)

### Day 4: Evaluate, protect and ship

Slides: https://sdaiaacademy.github.io/ae-203/slides/day4.md

- **Session 1: A small evaluation set**
  - Write golden cases with code-based checks
  - Report pass rates per category
  - Re-run the set after a change and compare
  - [Lab 4.1: Forty golden cases (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D4_1_eval_set.ipynb)
- **Session 2: One model grader, checked against labels**
  - Write a binary grader prompt with a parsable verdict
  - Measure agreement and kappa against labels
  - Decide when a model grader can be trusted
  - [Lab 4.2: A faithfulness grader against labels (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D4_2_grader.ipynb)
- **Session 3: Input and output checks**
  - Mask personal data before it reaches a model or a log
  - Flag instruction-like text in messages and retrieved pages
  - Count blocked, masked and passed cases with false positives
  - [Lab 4.3: Masking and flagging (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D4_3_safety_checks.ipynb)
- **Session 4: Packaging the assistant as a service**
  - Wrap the assistant in a web API with a health check
  - Test the service on recorded model responses
  - Report cost per 1,000 requests from measured usage
  - [Lab 4.4: Wasil as a tested web service (25 min)](https://sdaiaacademy.github.io/ae-203/labs/D4_4_service.ipynb)

### Capstone: Capstone project presentations

Slides: https://sdaiaacademy.github.io/ae-203/slides/capstone.md

## Capstone

An assistant for one of three supplied cases or an approved own case, submitted as a public repository with tests, an evaluation set of at least 40 cases and a README that reports results from two measured runs, cost per 1,000 requests and known limits, followed by an eight-minute defence and four minutes of questions

**What you submit:** A public GitHub repository with the service, its tests, an evaluation set of at least 40 cases with its run logs and commit history, and a README that reports results from two measured runs, cost per 1,000 requests and known limits. Then an eight-minute defence with four minutes of questions: the participant runs the evaluation, explains a failing case the assessor selects, and predicts the result of one new case the assessor adds.

**Rubric:**

- Working service and tests: 25%
- Structured output and tools: 20%
- Grounding and abstention: 20%
- Evaluation: 20%
- Safety checks and limits: 15%

## Outcomes

- **LO1** Compare the main model API shapes and identify what changes in code when an application switches provider or moves to a local model, given the same request written for three interfaces (Awareness) Evidence: an annotated comparison table that matches the reference on message structure, tool calls and usage reporting
- **LO2** Implement structured extraction from free-text messages with schema validation, bounded retries and a fallback path, given 300 synthetic Arabic and English rider messages and a target schema (Applied) Evidence: an extraction module with tests and a measured valid-output rate against a stated target
- **LO3** Implement tool calling for two services with typed arguments, argument validation and handling of tool errors, given a synthetic trip-status service and a ticket-creation service (Applied) Evidence: a passing test suite that includes malformed calls, timeouts and tool errors
- **LO4** Implement a grounded answering step that retrieves policy passages, cites them and declines when the corpus holds no answer, given 120 bilingual policy pages and 30 questions the corpus cannot answer (Applied) Evidence: answers whose citations are checked automatically and a measured abstention rate
- **LO5** Prepare a small evaluation set and measure the assistant with code-based checks and one model-graded check validated against labels, given 40 labelled cases across extraction, tool use and grounded answers (Applied) Evidence: an evaluation run with pass rates per category and the grader's agreement with the labels
- **LO6** Configure input and output checks for personal data, off-topic requests and instruction-like text inside retrieved content, given 30 seeded risky messages and documents (Applied) Evidence: a before-and-after table of blocked, masked and passed cases with false positives counted
- **LO7** Build a bilingual assistant service that combines structured extraction, tool calls and grounded answers behind a tested API, given the case corpus and services, a provider-neutral client and a cost limit per 1,000 requests (Performance) Evidence: a locally runnable service whose repository README reports evaluation results and cost from two measured runs

## Tools

- **Language model access:** a free hosted open-weight model, a locally served open-weight model, any commercial API
- **Provider-neutral client or gateway:** LiteLLM, an OpenAI-compatible local server such as llama.cpp server or Ollama
- **Schema validation and structured output:** Pydantic, Instructor, Outlines
- **Embeddings and vector search:** Sentence Transformers with FAISS, pgvector, Chroma
- **Lexical search:** SQLite full-text search, rank-bm25
- **Personal data detection:** Presidio, regular-expression and dictionary rules
- **Web service framework:** FastAPI, Flask
- **Evaluation harness:** pytest with custom assertions, promptfoo, Inspect

## Prerequisites

- FN-101 Python for Data and AI Work
- FN-102 Command Line, Git and Reproducible Projects
- FN-105 How Machine Learning and Language Models Work
- Calls a web API from Python and handles JSON
- Writes and runs unit tests

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

### HTTP and services

- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [gRPC: deadlines](https://grpc.io/docs/guides/deadlines/)
- [HTTPX: clients and connection pooling](https://www.python-httpx.org/advanced/clients/)

### National references

- [Personal Data Protection Law](https://sdaia.gov.sa/en/SDAIA/about/Documents/PersonalDataProtectionLaw.pdf)
- [Data Classification Policy (National Data Management Office)](https://sdaia.gov.sa/en/SDAIA/about/Documents/DataClassificationPolicy.pdf)
- [Generative AI Guideline for Government](https://sdaia.gov.sa/en/SDAIA/about/Files/GenAIGuidelinesForGovernmentENCompressed.pdf)
- [Generative AI Guideline for Public](https://sdaia.gov.sa/en/SDAIA/about/Files/GenerativeAIPublicEN.pdf)
- [Principles of AI Ethics](https://sdaia.gov.sa/en/SDAIA/about/Documents/ai-principles.pdf)

---

SDAIA Academy · AI Engineering Track · Building Applications on Language Models

Course version 2027.2.0 · engine 1.0.0 · built 2026-11-24 · commit ba00f32
