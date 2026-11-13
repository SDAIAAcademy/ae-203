# Assistant name: one line on what it does and for whom

Case: A (fares and refunds) / B (accessibility and lost property) / C (disruption notices) / own case, approved by
(trainer's name) on (date).

## Run it

```bash
uv sync
uv run pytest -q                       # tests, offline
uv run python evaluate.py --note "..." # the evaluation, logged to runs.jsonl
uv run uvicorn service:app             # the service on http://127.0.0.1:8000
```

Settings (environment): `LLM_PROVIDER`, `LLM_MODEL`, `WASIL_STATUS_TIMEOUT`, `WASIL_ABSTAIN_BELOW`, and others you
add. Keys go in `.env`, which is never committed.

## What it does

Three to five sentences: the requests it handles, the structured output, the tools, the corpus it answers from, and
what it hands to a person.

## Results from two measured runs

| | Run 1 | Run 2 |
|---|---|---|
| Commit | | |
| Provider and model | | |
| Cases | | |
| Pass rate: extraction | | |
| Pass rate: tool use | | |
| Pass rate: grounded | | |
| Abstention on unanswerable / false abstention | | |
| Grader agreement and kappa with your labels (if you use a grader) | | |

**What changed between the runs, and why:** one paragraph.

**Failures still open:** each with its case id and where the fault is (model, retrieval, rule or label).

## Cost per 1,000 requests

Measured on the evaluation set: model calls per request, input and output tokens per request, the prices you used
and where they come from (the provider's page and the date), and the result.

## Checks

What is masked before the model and the log, what is flagged, what the output check blocks, and what the log keeps.
The false positives you counted.

## Known limits

What the assistant does not do, where it fails, and what you would change next. Be specific: a limit stated with a
number is worth more than a promise.

## Use of AI tools

Which tools you used while building this, for what, and what you checked yourself.
