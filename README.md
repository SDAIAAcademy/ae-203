<!-- academy:title -->
# Building Applications on Language Models

بناء التطبيقات القائمة على النماذج اللغوية

AI Engineering Track · SDAIA Academy · AE-203 · Level 200

REPLACE: one line under the title: what participants can do after the course

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

**REPLACE: the name of the fictional organisation every lab works on.** REPLACE: two sentences on the case study and its synthetic data

<!-- academy:labs -->
## Labs

Every lab is a notebook in `labs/`. Open it in Google Colab from the course page, or run it locally with `uv`. Exercises raise `NotImplementedError` until they are done; the reference versions are in `labs/solutions/`.

| | Session | Lab | File |
|---|---|---|---|
| 1.1 | Day 1 · Session 1 | Count tokens for Arabic and English rider messages and estimate daily cost and latency for 10,000 messages | [`D1_1_count_tokens_arabic.ipynb`](labs/D1_1_count_tokens_arabic.ipynb) |
| 1.2 | Day 1 · Session 2 | Send the same request to a hosted and a local model through one client and compare the responses and usage fields | [`D1_2_send_same_request.ipynb`](labs/D1_2_send_same_request.ipynb) |
| 1.3 | Day 1 · Session 3 | Move the assistant's instructions into a versioned template and write two tests that pin its behaviour | [`D1_3_move_assistant_s.ipynb`](labs/D1_3_move_assistant_s.ipynb) |
| 1.4 | Day 1 · Session 4 | Add a timeout, a retry with backoff and a fallback model, and test them against a simulated slow endpoint | [`D1_4_add_timeout_retry.ipynb`](labs/D1_4_add_timeout_retry.ipynb) |
| 2.1 | Day 2 · Session 1 | Extract route, date and complaint type from 50 messages into a typed schema and measure the valid rate | [`D2_1_extract_route_date.ipynb`](labs/D2_1_extract_route_date.ipynb) |
| 2.2 | Day 2 · Session 2 | Feed validation errors back to the model, cap the retries and route failures to a human queue | [`D2_2_feed_validation_errors.ipynb`](labs/D2_2_feed_validation_errors.ipynb) |
| 2.3 | Day 2 · Session 3 | Expose the trip-status service as a tool and handle a correct call, a malformed call and a tool error | [`D2_3_expose_trip_status.ipynb`](labs/D2_3_expose_trip_status.ipynb) |
| 2.4 | Day 2 · Session 4 | Write one task as a fixed workflow and as a tool loop and compare steps, cost and failures on ten cases | [`D2_4_write_one_task.ipynb`](labs/D2_4_write_one_task.ipynb) |
| 3.1 | Day 3 · Session 1 | Chunk the Arabic and English policy pages two ways and index both versions | [`D3_1_chunk_arabic_english.ipynb`](labs/D3_1_chunk_arabic_english.ipynb) |
| 3.2 | Day 3 · Session 2 | Compare keyword, embedding and combined search on 30 questions with known source pages | [`D3_2_compare_keyword_embedding.ipynb`](labs/D3_2_compare_keyword_embedding.ipynb) |
| 3.3 | Day 3 · Session 3 | Generate answers that cite page and section and check automatically that each citation exists | [`D3_3_generate_answers_that.ipynb`](labs/D3_3_generate_answers_that.ipynb) |
| 3.4 | Day 3 · Session 4 | Add an abstention rule and measure it on 30 questions the corpus cannot answer | [`D3_4_add_abstention_rule.ipynb`](labs/D3_4_add_abstention_rule.ipynb) |
| 4.1 | Day 4 · Session 1 | Write 40 golden cases with code-based checks and run them against the assistant | [`D4_1_write_40_golden.ipynb`](labs/D4_1_write_40_golden.ipynb) |
| 4.2 | Day 4 · Session 2 | Write a binary faithfulness grader and measure its agreement with 30 labelled answers | [`D4_2_write_binary_faithfulness.ipynb`](labs/D4_2_write_binary_faithfulness.ipynb) |
| 4.3 | Day 4 · Session 3 | Mask personal data in messages and logs and flag instruction-like text found in retrieved pages | [`D4_3_mask_personal_data.ipynb`](labs/D4_3_mask_personal_data.ipynb) |
| 4.4 | Day 4 · Session 4 | Wrap the assistant in a web API with a health check and run the tests against recorded model responses | [`D4_4_wrap_assistant_web.ipynb`](labs/D4_4_wrap_assistant_web.ipynb) |
<!-- /academy:labs -->

## Capstone

An assistant for one of three supplied cases or an approved own case, submitted as a public repository with tests, an evaluation set of at least 40 cases and a README that reports results from two measured runs, cost per 1,000 requests and known limits, followed by an eight-minute defence and four minutes of questions

**Submission:** REPLACE: what participants submit and how: a public repository link, or a shared folder for a course without code

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

- REPLACE: every source the course cites, with its address, in course.json under "sources"; this list is written from there
<!-- /academy:sources -->

### National references

- Personal Data Protection Law and its implementing regulations: REPLACE: the address of the official text
- NDMO Data Classification Policy: REPLACE: the address of the official text
- SDAIA Generative AI Guidelines: REPLACE: the address of the official text
- SDAIA AI Ethics Principles: REPLACE: the address of the official text
