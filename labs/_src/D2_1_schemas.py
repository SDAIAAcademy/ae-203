# %% [markdown]
# # Lab 2.1 · Route, date and complaint type as a typed object
#
# Day 2 · Session 1 (Schemas for model output) · 25 min.
#
# Wasil must turn a rider's message into data the ticket service can use: which route, which day, what kind of
# complaint, and whether the rider asks for a refund. You write the schema, ask for it, validate each reply, and measure
# how often the model meets the schema on the first try.
#
# **AI policy.** Do the first attempt of this lab without AI assistance.
#
# **Reference state.** 50 of the 300 rider messages (`data/messages.jsonl`, 20 in quick mode) with their gold labels.
#
# **Tasks**
# - [ ] 1 · The schema: `RiderMessage` (5')
# - [ ] 2 · Ask for it with a JSON Schema response format (6')
# - [ ] 3 · Parse and validate one reply (7')
# - [ ] 4 · Fifty messages: valid rate and field accuracy (7')
# - [ ] ✱ Stretch · A strict schema the provider enforces

# %%
import os, sys, subprocess
from pathlib import Path

IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    REPO_URL = "https://github.com/SDAIAAcademy/llm-applications.git"
    if not Path("/content/llm-applications").exists():
        subprocess.run(["git", "clone", "-q", REPO_URL, "/content/llm-applications"], check=True)
    os.chdir("/content/llm-applications/labs")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements-colab.txt"], check=True)
    try:
        from google.colab import userdata  # the key from Colab's Secrets panel
        os.environ.setdefault("OPENROUTER_API_KEY", userdata.get("OPENROUTER_API_KEY"))
    except Exception:
        pass
else:
    while not Path("_tools").exists() and Path.cwd() != Path.cwd().parent:
        os.chdir("..")  # solutions/ notebooks run from labs/
sys.path.insert(0, os.getcwd())

import datetime as dt
import json
from collections import Counter
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

import llm
import darb as D
import wasil

SAMPLE = D.messages()[: llm.pick(50, 20)]
print(llm.describe(), "|", len(SAMPLE), "messages")
print(SAMPLE[0]["text"], "->", SAMPLE[0]["gold"])

# %% [markdown]
# ## 1 · The schema: `RiderMessage` (5')
#
# ✏️ **Exercise** · Define `RiderMessage` with: `route` (optional; `M1` to `M4`, or `B` and two digits), `date`
# (optional, a date), `complaint_type` (one of `delay`, `cancellation`, `overcharge`, `lost_item`, `accessibility`,
# `staff`, `cleanliness`, `other`) and `refund_requested` (bool). Write the digits of the pattern as `[0-9]`.

# %%
def make_schema():
    # BEGIN SOLUTION
    class RiderMessage(BaseModel):
        route: str | None = Field(default=None, pattern=r"^(M[1-4]|B[0-9]{2})$", description="Route id, such as M2 or B27")
        date: dt.date | None = Field(default=None, description="The service day the message is about")
        complaint_type: Literal["delay", "cancellation", "overcharge", "lost_item", "accessibility", "staff",
                                "cleanliness", "other"]
        refund_requested: bool
    return RiderMessage
    # END SOLUTION


# %%
try:
    RiderMessage = make_schema()
except NotImplementedError:
    RiderMessage = wasil.RiderMessage
print(json.dumps(RiderMessage.model_json_schema())[:300], "...")


class Loose(BaseModel):  # the same pattern written with \d
    route: str = Field(pattern=r"^B\d{2}$")


try:
    Loose(route="B٢٧")
    print("\\d accepts Arabic-Indic digits: B٢٧ is valid under ^B\\d{2}$")
except ValidationError:
    print("\\d rejected Arabic-Indic digits")
try:
    RiderMessage(route="B٢٧", complaint_type="delay", refund_requested=False)
    llm.check(False, "B٢٧ must be rejected by your schema")
except ValidationError:
    llm.check(True, "B٢٧ is rejected by your schema")

# %% [markdown]
# ## 2 · Ask for it with a JSON Schema response format (6')
#
# `response_format={"type": "json_schema", ...}` asks the provider to constrain the reply. Not every free model or
# gateway honours it, so the schema also goes into the system message and the reply is validated anyway.
#
# ✏️ **Exercise** · Write `ask(message)` that sends the message with the system prompt below (filled with the message's
# `received` date and the schema), the response format, and returns the reply's text.

# %%
SYSTEM = ("Extract the rider message as one JSON object matching this JSON Schema, and nothing else. "
          "Received on {received}; resolve words like 'yesterday' from that date.\n{schema}")


def ask(message: dict) -> str:
    # BEGIN SOLUTION
    schema = RiderMessage.model_json_schema()
    fmt = {"type": "json_schema", "json_schema": {"name": "RiderMessage", "schema": schema}}
    msgs = [{"role": "system", "content": SYSTEM.format(received=message["received"], schema=json.dumps(schema))},
            {"role": "user", "content": message["text"]}]
    return llm.text(llm.complete(msgs, response_format=fmt))
    # END SOLUTION


# %%
try:
    raw = ask(SAMPLE[1])
except NotImplementedError:
    raw = json.dumps(SAMPLE[1]["gold"])
print(SAMPLE[1]["text"], "\n->", raw)

# %% [markdown]
# ## 3 · Parse and validate one reply (7')
#
# Replies arrive wrapped in prose or a code fence, with a date in words, or with a value outside the list.
#
# ✏️ **Exercise** · Write `parse(reply)` that takes the text between the first `{` and the last `}`, validates it with
# `RiderMessage.model_validate_json`, and returns `(object, None)` or `(None, short_error)`.

# %%
def parse(reply: str):
    # BEGIN SOLUTION
    s, e = reply.find("{"), reply.rfind("}")
    try:
        return RiderMessage.model_validate_json(reply[s:e + 1] if s >= 0 else reply), None
    except ValidationError as ex:
        return None, "; ".join(f"{'.'.join(map(str, x['loc'])) or 'reply'}: {x['type']}" for x in ex.errors())
    # END SOLUTION


# %%
TRIES = ['Sure! ```json\n{"route": "B27", "date": "2026-11-14", "complaint_type": "delay", "refund_requested": true}\n```',
         '{"route": "B27", "date": "the twelfth of November", "complaint_type": "delay", "refund_requested": false}',
         '{"route": "B27", "date": null, "complaint_type": "late", "refund_requested": false}']
try:
    results = [parse(t) for t in TRIES]
except NotImplementedError:
    results = [(RiderMessage.model_validate_json(TRIES[0][TRIES[0].find("{"):TRIES[0].rfind("}") + 1]), None),
               (None, "date: date_from_datetime_parsing"), (None, "complaint_type: literal_error")]
for t, (obj, err) in zip(TRIES, results):
    print("valid  " if obj else "INVALID", (obj.model_dump(mode="json") if obj else err))
llm.check(results[0][0] is not None and results[1][0] is None and results[2][0] is None,
          "fence stripped; a date in words and an unknown type rejected")

# %% [markdown]
# ## 4 · Fifty messages: valid rate and field accuracy (7')
#
# Darb's target: **95% valid on the first try**. Below it, Lab 2.2's repair loop is needed.
#
# ✏️ **Exercise** · Write `run(sample)`: for each message, `ask`, `parse`, and record one row with the message id,
# its language, whether the reply was valid, the error, and the number of fields equal to the gold label (out of 4).

# %%
def run(sample: list[dict]) -> pd.DataFrame:
    rows = []
    for m in sample:
        # BEGIN SOLUTION
        obj, err = parse(ask(m))
        got = obj.model_dump(mode="json") if obj else {}
        right = sum(got.get(k) == v for k, v in m["gold"].items()) if obj else 0
        rows.append({"id": m["id"], "lang": m["lang"], "valid": obj is not None, "error": err or "", "fields_right": right})
        # END SOLUTION
    return pd.DataFrame(rows)


# %%
try:
    res = run(SAMPLE)
except NotImplementedError:
    res = pd.DataFrame([{"id": m["id"], "lang": m["lang"], "valid": True, "error": "", "fields_right": 4} for m in SAMPLE])
print(res.groupby("lang").agg(messages=("valid", "size"), valid_rate=("valid", "mean"), fields=("fields_right", "mean")).round(2))
valid_rate = res.valid.mean()
print(f"\nvalid on the first try: {valid_rate:.0%} (target 95%) | field accuracy of valid replies: "
      f"{res[res.valid].fields_right.sum() / (4 * max(1, res.valid.sum())):.0%}")
print("errors:", Counter(e.split(":")[0] for e in res.error if e))
print(llm.LEDGER)
llm.check(len(res) == len(SAMPLE), "every message has a row")

# %% [markdown]
# 🔍 **Look at** · which languages fail and which field. A valid reply can still be wrong: field accuracy is measured
# separately from validity.

# %% [markdown]
# ## ✱ Stretch · A strict schema the provider enforces
#
# Some providers and models enforce the schema while decoding (constrained decoding) when you set `"strict": true` in
# the response format. Send the same 20 messages with it and compare the valid rate.

# %%
def stretch():
    # BEGIN SOLUTION
    schema = RiderMessage.model_json_schema()
    fmt = {"type": "json_schema", "json_schema": {"name": "RiderMessage", "schema": schema, "strict": True}}
    ok = 0
    for m in SAMPLE[:20]:
        msgs = [{"role": "system", "content": SYSTEM.format(received=m["received"], schema=json.dumps(schema))},
                {"role": "user", "content": m["text"]}]
        ok += parse(llm.text(llm.complete(msgs, response_format=fmt)))[0] is not None
    print("valid with strict:", ok, "of 20")
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why does `^B\d{2}$` accept `B٢٧`, and why does that matter for Darb?
# <details><summary>Answer</summary>The pattern engine counts every Unicode digit as <code>\d</code>; the trip-status
# service only knows <code>B27</code>, so the call fails later instead of at validation.</details>
#
# 2. The reply is valid but the date is wrong. Which measurement shows it?
# <details><summary>Answer</summary>Field accuracy against the gold labels, not the valid rate.</details>
#
# 3. Why validate a reply produced under a JSON Schema response format?
# <details><summary>Answer</summary>Not every provider enforces it, and a schema cannot express every rule (a date
# that is not in the future, a route that exists).</details>
#
# **Carry forward.** `wasil.RiderMessage` is the same schema; Lab 2.2 starts from it.
