# Capstone: an assistant you can defend

You build one assistant on Darb's data, behind a tested web API. You measure it twice, and you defend it live. It is
the work of Labs 4.1 to 4.4, finished and extended to one of the three cases below. You can also bring a case of your
own if the trainer approves it.

## What you submit

A **public GitHub repository** with:

- the service (`/health` and `/ask` at least) and its tests, which run with `pytest` and with no network;
- an evaluation set of **at least 40 cases** for your assistant, with code-based checks, and its **run logs**
  (`runs.jsonl`: time, commit, provider, model, pass rate per category);
- a commit history that shows the work as it happened;
- a README, from [`starter/README_TEMPLATE.md`](starter/README_TEMPLATE.md), that reports the results of **two measured
  runs** (before and after one change you chose), the **cost per 1,000 requests** from measured token use, and the
  **known limits**.

Then you give an **eight-minute defence with four minutes of questions**. You run the evaluation, you explain a failing
case the assessor picks, and you predict the result of one new case the assessor adds before you run it.

## The three cases

All three use the Darb data in `labs/data/` and the helpers in `labs/` (`llm.py`, `darb.py`, `wasil.py`).

### A · Fares and refunds assistant

Riders ask about fares, caps, concessions and refunds (policies P01 to P05, P12 and P13), and they complain about
delays and cancellations.

- Structured output: the complaint fields from Day 2, plus a `refund_eligible` decision that **code** makes from the
  trip status and P03 or P04, never the model.
- Tools: `get_trip_status`, `create_ticket` with the refund flag.
- Grounding: answers cite the section they used and never cite the superseded P31.
- Evaluation: at least 15 refund decisions whose correct outcome you work out by hand from the policy.

### B · Accessibility and lost-property assistant

Riders ask about step-free access, assistance, companions and lost items (P06, P07, P29, P30 and the station
pages P44 to P60), in Arabic and English.

- Structured output: a lost-item report (route, date, item, where it was last seen) and an assistance request (station,
  date, kind of assistance).
- Tools: `create_ticket` with the category `lost_item` or `accessibility`; one more tool you design (for example,
  a station's lifts and their status), with typed arguments and errors.
- Grounding: the station pages are short and similar to each other; measure whether retrieval finds the right station.
- Safety: P30 holds an instruction planted for automated assistants; your checks must flag it, and your evaluation
  must include it.

### C · Disruption notices for operations

Mishal's operations team writes notices to riders when a line is late or trips are cancelled. The assistant drafts a
bilingual notice from the network status of a day, for a person to approve.

- Structured output: a `Notice` (routes, date, delay, cancelled trips, reason, the English text and the Arabic text,
  and a list of the policy sections it relies on).
- Tools: `get_trip_status` for every route; the assistant must not invent a route's status.
- Grounding: what riders may claim (P03, P04, P20, P21) is quoted from the policy and cited.
- Evaluation: notices for the 15 days of `network.json`, checked by code: every number in the notice is in the
  status data, both languages give the same numbers, and every cited section exists and is in force.

### An own case

It has to involve structured output, at least one tool and grounded answers on a corpus you are allowed to use and
publish. Bring a one-paragraph description and a sample of the data to the trainer by the end of Day 4. Never put
personal or classified data in a public repository: use synthetic data the way Darb's data is synthetic.

## The starter

[`starter/`](starter/) is a working minimum on the reference assistant of Day 4:

| File | What it does |
|---|---|
| `service.py` | the FastAPI app: `/health`, `/ask`, settings from the environment |
| `evaluate.py` | runs a case file through the assistant, prints pass rates per category, appends a line to `runs.jsonl` |
| `tests/test_service.py` | five tests on the scripted stand-in: no network, no key |
| `README_TEMPLATE.md` | the README your repository submits, with every section the rubric reads |

From `labs/`:

```bash
uv run python capstone/starter/evaluate.py            # the 40 golden cases, logged to capstone/starter/runs.jsonl
uv run pytest capstone/starter/tests -q               # the tests
uv run uvicorn service:app --app-dir capstone/starter # the service on http://127.0.0.1:8000
```

To start your repository, copy `starter/` together with `llm.py`, `darb.py`, `wasil.py`, `pyproject.toml` and `data/`
into a new folder. The starter finds the helpers next to it or two folders up. Then replace the reference assistant
with yours, one step at a time, and run the evaluation after each step.

## How it is scored

| Criterion | Weight | Full marks look like |
|---|---|---|
| Working service and tests | 25 | the service starts with one command; tests run offline and cover bad requests, tool errors and a timeout |
| Structured output and tools | 20 | typed schemas, validated tool arguments, repair and a fallback path with a measured valid-output rate |
| Grounding and abstention | 20 | citations checked by code; an abstention threshold chosen on both error rates and stated |
| Evaluation | 20 | at least 40 cases, two logged runs with one stated change between them, failures explained |
| Safety checks and limits | 15 | personal data masked before the model and the log, instructions flagged, an output check, limits stated honestly |

The repository is 60% of the course grade and the live defence is 20%. To pass you need 70% overall, with at least 60%
on this rubric.

## After the course

The follow-up task: extend your evaluation set to 80 cases and run it again after one change of model. Report what
changed and why.
