# Building Applications on Language Models: labs

## Quick start

- Google Colab: open a notebook from the course page; its first cell clones this repository.
- Locally: clone the repository, then open the notebooks in `labs/` with Jupyter.

| Unit | Session | Notebook |
|---|---|---|
| Day 1 | Session 1 · Tokens, context and cost | [`D1_1_count_tokens_arabic.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D1_1_count_tokens_arabic.ipynb) |
| Day 1 | Session 2 · Three API shapes, one interface | [`D1_2_send_same_request.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D1_2_send_same_request.ipynb) |
| Day 1 | Session 3 · Prompts as versioned code | [`D1_3_move_assistant_s.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D1_3_move_assistant_s.ipynb) |
| Day 1 | Session 4 · Streaming, timeouts and retries | [`D1_4_add_timeout_retry.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D1_4_add_timeout_retry.ipynb) |
| Day 2 | Session 1 · Schemas for model output | [`D2_1_extract_route_date.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D2_1_extract_route_date.ipynb) |
| Day 2 | Session 2 · Validation, retry and fallback | [`D2_2_feed_validation_errors.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D2_2_feed_validation_errors.ipynb) |
| Day 2 | Session 3 · Tool calling | [`D2_3_expose_trip_status.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D2_3_expose_trip_status.ipynb) |
| Day 2 | Session 4 · Workflow or agent | [`D2_4_write_one_task.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D2_4_write_one_task.ipynb) |
| Day 3 | Session 1 · Chunking and indexing a policy corpus | [`D3_1_chunk_arabic_english.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D3_1_chunk_arabic_english.ipynb) |
| Day 3 | Session 2 · Lexical, dense and hybrid search | [`D3_2_compare_keyword_embedding.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D3_2_compare_keyword_embedding.ipynb) |
| Day 3 | Session 3 · Answers with citations | [`D3_3_generate_answers_that.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D3_3_generate_answers_that.ipynb) |
| Day 3 | Session 4 · Saying the answer is not there | [`D3_4_add_abstention_rule.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D3_4_add_abstention_rule.ipynb) |
| Day 4 | Session 1 · A small evaluation set | [`D4_1_write_40_golden.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D4_1_write_40_golden.ipynb) |
| Day 4 | Session 2 · One model grader, checked against labels | [`D4_2_write_binary_faithfulness.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D4_2_write_binary_faithfulness.ipynb) |
| Day 4 | Session 3 · Input and output checks | [`D4_3_mask_personal_data.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D4_3_mask_personal_data.ipynb) |
| Day 4 | Session 4 · Packaging the assistant as a service | [`D4_4_wrap_assistant_web.ipynb`](https://colab.research.google.com/github/SDAIAAcademy/llm-applications/blob/main/labs/D4_4_wrap_assistant_web.ipynb) |

The notebooks are generated from the percent-format sources in `labs/_src/` by `labs/_tools/py2nb.py` (`uv run python _tools/py2nb.py` from `labs/`), which also writes the solutions to `labs/solutions/`. Edit the sources, not the notebooks.
