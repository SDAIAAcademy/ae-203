# %% [markdown]
# # Lab 4.1 · Forty golden cases
#
# Day 4 · Session 1 (A small evaluation set) · 25 min.
#
# Wasil now extracts, calls tools and answers from policies. Before anyone changes a prompt, a model or a threshold,
# the team needs one command that says what still works. You read the 40 golden cases, add two of your own, write a
# code-based check for each category, run the set, and re-run it after one change.
#
# **Reference state.** `wasil.Wasil`, the reference assistant built from Days 1 to 3, and `data/eval/golden.jsonl`
# (15 extraction, 10 tool-use and 15 grounded cases, five of them unanswerable).
#
# **Tasks**
# - [ ] 1 · Read the cases and write two of your own (6')
# - [ ] 2 · A check per category (7')
# - [ ] 3 · Run the set: pass rates per category (6')
# - [ ] 4 · Change one setting and re-run (6')
# - [ ] ✱ Stretch · A run log with a timestamp and the commit

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

import json
import shutil
from collections import Counter
from datetime import datetime, timezone

import pandas as pd

import llm
import darb as D
import wasil

OUT = Path("artifacts/lab41")
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)
GOLDEN = D.load_jsonl("eval/golden.jsonl")
print(llm.describe(), "|", Counter(c["category"] for c in GOLDEN))
for cat in ("extraction", "tool_use", "grounded"):
    print(json.dumps(next(c for c in GOLDEN if c["category"] == cat), ensure_ascii=False))

# %% [markdown]
# ## 1 · Read the cases and write two of your own (6')
#
# A golden case is an input, the day it was received, and what must be true of the output. It is checked by code, not
# by eye.
#
# ✏️ **Exercise** · Write `my_cases()`: two new cases in the same format, ids `GC-41` and `GC-42`. One extraction case
# from a message you write (an Arabic one, with the gold fields), and one grounded case the corpus cannot answer.

# %%
def my_cases() -> list[dict]:
    # BEGIN SOLUTION
    return [
        {"id": "GC-41", "category": "extraction", "received": "2026-11-15",
         "input": "نسيت جوالي في الخط الأخضر أمس",
         "expect": {"route": "M2", "date": "2026-11-14", "complaint_type": "lost_item", "refund_requested": False}},
        {"id": "GC-42", "category": "grounded", "received": "2026-11-15",
         "input": "Does Darb sell gift vouchers for the metro?", "expect": {"abstain": True}},
    ]
    # END SOLUTION


# %%
try:
    CASES = GOLDEN + my_cases()
except NotImplementedError:
    CASES = GOLDEN
print(len(CASES), "cases")

# %% [markdown]
# ## 2 · A check per category (7')
#
# ✏️ **Exercise** · Write `check_case(case, w)` that runs the assistant and returns `(passed, detail)`:
# - **extraction**: `wasil.extract(input, received)` returns an object whose fields equal `expect`;
# - **tool_use**: `w.answer(...)` made a `get_trip_status` call with the expected arguments, and the answer contains
#   `answer_contains`;
# - **grounded**: if `expect["abstain"]`, the answer abstained; otherwise it did not, it cites `expect["cite"]`, and it
#   contains `answer_contains`.
#
# `detail` is a short string that says what failed.

# %%
def check_case(case: dict, w: wasil.Wasil) -> tuple[bool, str]:
    e = case["expect"]
    # BEGIN SOLUTION
    if case["category"] == "extraction":
        obj, _, err = wasil.extract(case["input"], case["received"])
        got = obj.model_dump(mode="json") if obj else None
        if got is None:
            return False, f"no valid object: {err[:60]}"
        wrong = [k for k in e if got.get(k) != e[k]]
        return not wrong, f"wrong {wrong}" if wrong else "ok"
    out = w.answer(case["input"], case["received"])
    if case["category"] == "tool_use":
        called = any(c["name"] == "get_trip_status" and c["arguments"] == e["args"] for c in out["tool_calls"])
        has = e["answer_contains"] in out["answer"]
        return called and has, "ok" if called and has else f"called={called} contains={has}: {out['answer'][:50]}"
    if e["abstain"]:
        return out["abstained"], "ok" if out["abstained"] else f"answered: {out['answer'][:50]}"
    ok = not out["abstained"] and e["cite"] in out["citations"] and e["answer_contains"] in out["answer"]
    return ok, "ok" if ok else f"cites {out['citations']}, abstained={out['abstained']}: {out['answer'][:50]}"
    # END SOLUTION


# %%
w = wasil.Wasil()
try:
    print(check_case(CASES[0], w), check_case(CASES[15], w), check_case(CASES[35], w))
except NotImplementedError:
    print("check_case not written yet")

# %% [markdown]
# ## 3 · Run the set: pass rates per category (6')
#
# ✏️ **Exercise** · Write `run_set(cases, w)` that returns a DataFrame with one row per case: id, category, passed,
# detail. Print the pass rate per category and every failure.

# %%
def run_set(cases: list[dict], w: wasil.Wasil) -> pd.DataFrame:
    # BEGIN SOLUTION
    rows = []
    for c in cases:
        ok, detail = check_case(c, w)
        rows.append({"id": c["id"], "category": c["category"], "passed": ok, "detail": detail})
    return pd.DataFrame(rows)
    # END SOLUTION


# %%
try:
    RUN1 = run_set(CASES, wasil.Wasil())
except NotImplementedError:
    RUN1 = pd.DataFrame([{"id": c["id"], "category": c["category"], "passed": True, "detail": "reference"} for c in CASES])
print(RUN1.groupby("category").passed.agg(["sum", "count", "mean"]).round(2))
print(f"overall: {RUN1.passed.mean():.0%}")
print(RUN1[~RUN1.passed].to_string(index=False, max_colwidth=70))
print(llm.LEDGER)

# %% [markdown]
# 🔍 **Look at** · each failure's detail. Is it the model (a wrong field), the retrieval (the wrong section), or the rule
# (an abstention threshold)? The category tells you where to look first.

# %% [markdown]
# ## 4 · Change one setting and re-run (6')
#
# Ziyad proposes to lower the abstention threshold from 7 to 4 "so Wasil answers more questions".
#
# ✏️ **Exercise** · Run the set again on an assistant with `ABSTAIN_BELOW = 4.0`, and print the cases whose outcome
# changed between the two runs.

# %%
def rerun() -> pd.DataFrame:
    # BEGIN SOLUTION
    w2 = wasil.Wasil()
    w2.ABSTAIN_BELOW = 4.0
    run2 = run_set(CASES, w2)
    both = RUN1.merge(run2, on=["id", "category"], suffixes=("_before", "_after"))
    print(both[both.passed_before != both.passed_after][["id", "category", "passed_before", "passed_after", "detail_after"]]
          .to_string(index=False, max_colwidth=60))
    return run2
    # END SOLUTION


# %%
try:
    RUN2 = rerun()
    print(pd.DataFrame({"threshold 7": RUN1.groupby("category").passed.mean(),
                        "threshold 4": RUN2.groupby("category").passed.mean()}).round(2))
except NotImplementedError:
    RUN2 = RUN1
llm.check(len(RUN2) == len(CASES), "the whole set ran again, not only the cases the change was meant for")

# %% [markdown]
# ## ✱ Stretch · A run log with a timestamp and the commit
#
# The capstone asks for evaluation run logs with timestamps and the commit they ran on. Append one line per run to
# `OUT / "runs.jsonl"`.

# %%
def stretch():
    # BEGIN SOLUTION
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = "unknown"
    line = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "commit": commit or "unknown",
            "provider": llm.PROVIDER, "model": llm.MODEL, "cases": len(RUN1),
            "pass_rate": {k: round(v, 3) for k, v in RUN1.groupby("category").passed.mean().items()}}
    with (OUT / "runs.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
    print(line)
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why check the whole set after a change meant only for grounded answers?
# <details><summary>Answer</summary>Changes leak: a threshold, a prompt or a model touches more than its target, and
# only the whole set shows it.</details>
#
# 2. A case fails because its gold label is wrong. What do you do?
# <details><summary>Answer</summary>Fix the label with a note in the history, and never edit a label to make a run
# pass.</details>
#
# 3. Forty cases pass at 85%. What does that number not tell you?
# <details><summary>Answer</summary>How riders' real messages differ from the cases; add real declined and complained-about
# cases over time.</details>
#
# **Carry forward.** The capstone's evaluation set starts from these 42 cases; the follow-up task extends it to 80.
