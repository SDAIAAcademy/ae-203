# %% [markdown]
# # Lab 4.2 · A faithfulness grader against labels
#
# Day 4 · Session 2 (One model grader, checked against labels) · 25 min.
#
# Some properties cannot be checked by code: is everything in this answer supported by its passage? A model can grade
# that, but a grader is itself a model with its own errors. Before trusting it, you measure its agreement with 30
# answers that people labelled.
#
# **Reference state.** `data/eval/grader_labels.jsonl`: 30 (question, passage, answer) triples labelled 1 (faithful)
# or 0 (not faithful), with the kind of fault: a changed number, or an unsupported addition.
#
# **Tasks**
# - [ ] 1 · The grader prompt (6')
# - [ ] 2 · Grade one answer and parse the verdict (7')
# - [ ] 3 · Agreement and kappa on 30 labels (6')
# - [ ] 4 · Read the disagreements (6')
# - [ ] ✱ Stretch · Swap the order of passage and answer

# %%
import os, sys, subprocess
from pathlib import Path

IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    REPO_URL = "https://github.com/SDAIAAcademy/ae-203.git"
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
import re
import pandas as pd

import llm
import darb as D

LABELS = D.load_jsonl("eval/grader_labels.jsonl")
print(llm.describe(), "|", len(LABELS), "labelled answers |", pd.Series([x["kind"] for x in LABELS]).value_counts().to_dict())
print(json.dumps(LABELS[3], ensure_ascii=False, indent=1))

# %% [markdown]
# ## 1 · The grader prompt (6')
#
# A good grader prompt asks one binary question, defines it, and asks for a verdict code can parse.
#
# ✏️ **Exercise** · Write `GRADER`, the system prompt: the grader judges whether an answer is faithful to a passage
# (every claim and every number in the answer appears in the passage; anything added makes it unfaithful), and replies
# with one JSON object `{"verdict": "PASS" | "FAIL", "reason": "..."}` and nothing else.

# %%
def grader_prompt() -> str:
    # BEGIN SOLUTION
    return ("You are a strict grader of faithfulness. An answer is faithful when every claim and every number in it "
            "appears in the passage. Anything the passage does not state, even if true elsewhere, makes it unfaithful. "
            'Reply with one JSON object and nothing else: {"verdict": "PASS" or "FAIL", "reason": "one sentence"}.')
    # END SOLUTION


# %%
try:
    GRADER = grader_prompt()
except NotImplementedError:
    GRADER = ("You are a strict grader of faithfulness. An answer is faithful when every claim and number appears in the "
              'passage. Reply with JSON only: {"verdict": "PASS" or "FAIL", "reason": "..."}.')
print(GRADER)
llm.check("PASS" in GRADER and "FAIL" in GRADER, "the verdict is a closed choice")

# %% [markdown]
# ## 2 · Grade one answer and parse the verdict (7')
#
# ✏️ **Exercise** · Write `grade(item)`: send `GRADER` and a user message `PASSAGE: ...` then `ANSWER: ...` on the next
# line; parse the JSON between the first `{` and the last `}`; return 1 for PASS, 0 for FAIL, and `None` when the reply
# cannot be parsed (count those, never guess them).

# %%
def grade(item: dict, order: str = "passage first") -> int | None:
    user = (f"PASSAGE: {item['passage']}\nANSWER: {item['answer']}" if order == "passage first"
            else f"ANSWER: {item['answer']}\nPASSAGE: {item['passage']}")
    # BEGIN SOLUTION
    reply = llm.text(llm.complete([{"role": "system", "content": GRADER}, {"role": "user", "content": user}]))
    s, e = reply.find("{"), reply.rfind("}")
    try:
        verdict = json.loads(reply[s:e + 1])["verdict"].strip().upper()
    except (ValueError, KeyError, AttributeError):
        return None
    return {"PASS": 1, "FAIL": 0}.get(verdict)
    # END SOLUTION


# %%
try:
    print([(x["label"], grade(x)) for x in LABELS[:5]])
except NotImplementedError:
    print("grade not written yet")

# %% [markdown]
# ## 3 · Agreement and kappa on 30 labels (6')
#
# Agreement is the share of answers where grader and label agree. Kappa corrects for the agreement two raters would reach
# by chance: `(p_o - p_e) / (1 - p_e)`, where `p_e` is the chance that both say PASS plus the chance that both say FAIL.
#
# ✏️ **Exercise** · Write `agreement(labels, verdicts)` that returns agreement, Cohen's kappa, and the confusion counts.
# Leave unparsed verdicts out and report how many there were.

# %%
def agreement(labels: list[int], verdicts: list) -> dict:
    # BEGIN SOLUTION
    pairs = [(l, v) for l, v in zip(labels, verdicts) if v is not None]
    n = len(pairs)
    po = sum(l == v for l, v in pairs) / n
    pl, pv = sum(l for l, _ in pairs) / n, sum(v for _, v in pairs) / n
    pe = pl * pv + (1 - pl) * (1 - pv)
    return {"n": n, "unparsed": len(labels) - n, "agreement": round(po, 2),
            "kappa": round((po - pe) / (1 - pe), 2) if pe < 1 else 0.0,
            "pass_pass": sum(l == 1 and v == 1 for l, v in pairs), "fail_fail": sum(l == 0 and v == 0 for l, v in pairs),
            "label_pass_grader_fail": sum(l == 1 and v == 0 for l, v in pairs),
            "label_fail_grader_pass": sum(l == 0 and v == 1 for l, v in pairs)}
    # END SOLUTION


# %%
try:
    VERDICTS = [grade(x) for x in LABELS]
except NotImplementedError:
    VERDICTS = [x["label"] for x in LABELS]
try:
    A = agreement([x["label"] for x in LABELS], VERDICTS)
except NotImplementedError:
    A = {"agreement": None, "kappa": None}
print(A)
TRUST = A.get("agreement") is not None and A["agreement"] >= 0.85 and A["kappa"] >= 0.6
print("trust the grader for the evaluation set:", TRUST, "(rule: agreement >= 0.85 and kappa >= 0.6, set before the run)")

# %% [markdown]
# ## 4 · Read the disagreements (6')
#
# ✏️ **Exercise** · Write `disagreements()`: a DataFrame of the items where the verdict differs from the label, with the
# kind of fault, the label, the verdict and the answer. Which kind of fault does the grader miss?

# %%
def disagreements() -> pd.DataFrame:
    # BEGIN SOLUTION
    return pd.DataFrame([{"id": x["id"], "kind": x["kind"], "label": x["label"], "verdict": v, "answer": x["answer"][:80]}
                         for x, v in zip(LABELS, VERDICTS) if v != x["label"]])
    # END SOLUTION


# %%
try:
    DIS = disagreements()
    print(DIS.to_string(index=False) if len(DIS) else "no disagreement")
    print(pd.DataFrame({"kind": [x["kind"] for x in LABELS], "right": [v == x["label"] for x, v in zip(LABELS, VERDICTS)]})
          .groupby("kind").right.mean().round(2))
except NotImplementedError:
    print("disagreements not written yet")
print(llm.LEDGER)

# %% [markdown]
# 🔍 **Look at** · the label itself, for each disagreement. Sometimes the label is wrong; fix it with a note. Never fix a
# label to raise the agreement.

# %% [markdown]
# ## ✱ Stretch · Swap the order of passage and answer
#
# Graders can be sensitive to the order of their inputs. Grade all 30 with the answer first and compare the agreement.

# %%
def stretch():
    # BEGIN SOLUTION
    swapped = [grade(x, order="answer first") for x in LABELS]
    print("answer first:", agreement([x["label"] for x in LABELS], swapped))
    print("verdicts that changed:", sum(a != b for a, b in zip(VERDICTS, swapped)))
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why measure kappa and not only agreement?
# <details><summary>Answer</summary>With mostly faithful answers, a grader that always says PASS agrees often; kappa
# gives it no credit for that.</details>
#
# 2. Suppose your grader agrees on changed numbers but misses unsupported additions. Can it still be used?
# <details><summary>Answer</summary>Only for what it was shown to judge well, and with its known weakness stated next
# to every number it produces.</details>
#
# 3. Why ask for a binary verdict rather than a score from 1 to 10?
# <details><summary>Answer</summary>A binary question is easier to define, to label and to agree on; a scale invites
# drift between runs and graders.</details>
#
# **Carry forward.** The capstone README reports the grader's agreement with the labels next to every graded result.
