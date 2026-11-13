# Building Applications on Language Models: labs

Hands-on notebooks for the SDAIA Academy course **AE-203 Building Applications on Language Models (بناء التطبيقات القائمة على النماذج اللغوية)**. Every lab builds a piece of **Wasil (واصل)**, the bilingual rider assistant of **Darb Transit Authority**, a fictional city transport authority with four metro lines, eight bus routes, a trip-status service, a ticket service and 120 policy pages in Arabic and English. Each lab starts from a supplied reference state, so none depends on another.

All labs use **free hosted models over an API**, or no model at all. Nothing downloads a model, and a laptop CPU or a Colab CPU runtime is enough.

## Quick start

**1 · Get a free OpenRouter key.** Create one at <https://openrouter.ai/keys>. Free models have an id ending in `:free` and request limits per minute and per day (see <https://openrouter.ai/docs/api-reference/limits>). Identical requests are replayed from `labs/cache/`, so re-running a cell costs nothing.

**2a · Google Colab**
1. Open a notebook from the [course page](https://sdaiaacademy.github.io/llm-applications/), or directly: `https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/<notebook>.ipynb`.
2. In the **Secrets** panel add `OPENROUTER_API_KEY` and turn on notebook access.
3. Run the first cell. It clones this repository and installs `requirements-colab.txt`.

**2b · Local**
```bash
git clone https://github.com/SDAIAAcademy/llm-applications
cd llm-applications/labs
cp .env.example .env           # then paste your key into .env
uv sync                        # creates the environment from pyproject.toml (uv.lock pins every version)
uv run python prepare_data.py  # optional: rewrites data/ (committed; the same bytes every time)
uv run jupyter lab
```

**Without a key.** When no key is set, `llm.py` uses the course's **scripted stand-in model**: rules that imitate what each lab needs, including typical model mistakes, so every cell runs offline. Its answers are not a model's answers; run with a key before you trust a number about model quality.

**Windows and long folder paths.** If an import fails with "The filename or extension is too long", keep the environment in a short folder: set `UV_PROJECT_ENVIRONMENT` to a short path (a folder at the root of your drive) before `uv sync`.

## Models and providers

| Setting (`.env`) | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `openrouter` when a key is set, else `scripted` | `openrouter`, `local` (any OpenAI-compatible server) or `scripted` |
| `LLM_MODEL` | `google/gemma-4-31b-it:free` | any free model with tool support from <https://openrouter.ai/models> |
| `LLM_FALLBACKS` | `google/gemma-4-26b-a4b-it:free,nvidia/nemotron-3-ultra-550b-a55b:free` | tried in order on a 429 or a server error |
| `LOCAL_BASE_URL`, `LOCAL_MODEL` | `http://127.0.0.1:8765/v1`, `wasil-stand-in` | Ollama, llama.cpp server, vLLM or LiteLLM serve the same protocol |
| `LLM_CACHE` | `1` | `0` sends every request to the model |
| `DARB_QUICK` | `0` | `1` shrinks samples to save free requests |

Free models change often. If the default disappears or is busy, pick another free model with tool support.

## Notebooks

| Day | Session | Notebook | Model calls |
|---|---|---|---|
| 1 | Tokens, context and cost | [`D1_1_tokens_cost.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D1_1_tokens_cost.ipynb) | none |
| 1 | Three API shapes, one interface | [`D1_2_three_shapes.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D1_2_three_shapes.ipynb) | two |
| 1 | Prompts as versioned code | [`D1_3_prompt_versions.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D1_3_prompt_versions.ipynb) | four |
| 1 | Streaming, timeouts and retries | [`D1_4_retries.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D1_4_retries.ipynb) | none (simulated endpoint) |
| 2 | Schemas for model output | [`D2_1_schemas.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D2_1_schemas.ipynb) | 50 |
| 2 | Validation, retry and fallback | [`D2_2_repair_fallback.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D2_2_repair_fallback.ipynb) | about 70 |
| 2 | Tool calling | [`D2_3_tool_calling.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D2_3_tool_calling.ipynb) | about 10 |
| 2 | Workflow or agent | [`D2_4_workflow_agent.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D2_4_workflow_agent.ipynb) | about 50 |
| 3 | Chunking and indexing a policy corpus | [`D3_1_chunking.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D3_1_chunking.ipynb) | none |
| 3 | Lexical, dense and hybrid search | [`D3_2_search.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D3_2_search.ipynb) | none |
| 3 | Answers with citations | [`D3_3_citations.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D3_3_citations.ipynb) | 60 |
| 3 | Saying the answer is not there | [`D3_4_abstention.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D3_4_abstention.ipynb) | 60 |
| 4 | A small evaluation set | [`D4_1_eval_set.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D4_1_eval_set.ipynb) | about 100 |
| 4 | One model grader, checked against labels | [`D4_2_grader.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D4_2_grader.ipynb) | 30 |
| 4 | Input and output checks | [`D4_3_safety_checks.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D4_3_safety_checks.ipynb) | about 20 |
| 4 | Packaging the assistant as a service | [`D4_4_service.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D4_4_service.ipynb) | about 20, then none (replayed) |

Exercises are marked **✏️ Exercise** and raise `NotImplementedError` until you fill them in; the cell after each one supplies a reference result, so the rest of the notebook still runs. Complete versions are in `solutions/`. Stretch cells are optional.

The notebooks are generated from the percent-format sources in `_src/` by `_tools/py2nb.py` (`uv run python _tools/py2nb.py` from `labs/`), which also writes the solutions. Edit the sources, not the notebooks. Lab outputs go to `artifacts/` and model responses to `cache/`; delete both before running the course's `academy check`, which reports them as course files.

## The case study: Darb Transit Authority

Synthetic and deterministic (seed 203), dated around **Sunday 15 November 2026**, the labs' "today". No real person, organisation or personal data.

| Data | File | Contents |
|---|---|---|
| Rider messages | `data/messages.jsonl` | 300 messages: 120 English, 105 Arabic, 40 Arabizi, 35 mixed; gold route, date, complaint type and refund flag; 41 carry fake personal data, 9 carry embedded instructions |
| Policy pages | `data/policies/P01_en.md` to `P60_ar.md` | 60 policies in English and Arabic, with numbered sections (`P03.1`); P31 is superseded by P03; P30 carries a planted instruction |
| Network and service days | `data/network.json` | 4 metro lines, 8 bus routes, status of every route on every day from 1 to 15 November; route B33's feed answers slowly |
| Questions | `data/questions/` | 30 answerable questions with their source section, 30 the corpus cannot answer |
| Evaluation | `data/eval/` | 40 golden cases (15 extraction, 10 tool use, 15 grounded answers) and 30 answers labelled faithful or not |
| Safety | `data/safety/risky.jsonl` | 30 seeded items: 12 with personal data, 6 messages and 6 documents with instructions, 6 harmless look-alikes |
| API shapes | `data/reference/` | one request in three shapes and the reference comparison table (Lab 1.2) |

## Helpers

| Module | What it holds |
|---|---|
| `llm.py` | `complete()` (one Chat Completions call to any provider, cached, with fallbacks), `text()`, `count_tokens()`, `LEDGER` (calls and tokens), `serve_local()` (an OpenAI-compatible server on localhost), `SlowEndpoint` (planned delays and errors), the scripted stand-in model |
| `darb.py` | the data loaders, `TripStatus` and `Tickets` (the two services), `pages()`, chunkers, `BM25`, `Vectors`, `rrf`, `Retriever`, `mask_pii()`, `instruction_like()` |
| `wasil.py` | the reference assistant of Day 4 and the capstone: `RiderMessage`, `extract()`, `TOOLS`, `Wasil.answer()` |
| `prepare_data.py`, `policies_src.py` | the data generator and the policy texts |
