# %% [markdown]
# # Lab 3.4 · Saying the answer is not there
#
# Day 3 · Session 4 (Saying the answer is not there) · 25 min.
#
# Riders ask things Darb's policies do not cover: cryptocurrency, a line that does not exist, drivers' pay. Search
# always returns *something*, and a model given something tends to answer. You build an abstention rule from two
# signals (the retrieval score and the model's own "not in corpus"), choose its threshold on measured rates, and write
# what the rider reads.
#
# **Reference state.** `darb.Retriever` without superseded pages, 30 answerable and 30 unanswerable questions.
#
# **Tasks**
# - [ ] 1 · Scores of answerable and unanswerable questions (6')
# - [ ] 2 · An abstention rule (6')
# - [ ] 3 · Thresholds against both rates (7')
# - [ ] 4 · What the rider reads (6')
# - [ ] ✱ Stretch · A threshold per language

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

import re
import pandas as pd

import llm
import darb as D

R = D.Retriever()
YES = D.load_jsonl("questions/answerable.jsonl")
NO = D.load_jsonl("questions/unanswerable.jsonl")
SYSTEM = ("Answer the rider's question only from the passages. Cite the passage id in square brackets, like [P03.1]. "
          "If the passages do not hold the answer, reply exactly NOT_IN_CORPUS.")
print(llm.describe(), "|", len(YES), "answerable,", len(NO), "unanswerable, e.g.", NO[0]["question"])

# %% [markdown]
# ## 1 · Scores of answerable and unanswerable questions (6')
#
# `R.best_bm25(q)` is the BM25 score of the best chunk for a question. If unanswerable questions score lower, the score
# is a signal.
#
# ✏️ **Exercise** · Write `score_table()`: one row per question with its id, language, `answerable` (bool) and its best
# BM25 score. Print the quartiles of the score for each group.

# %%
def score_table() -> pd.DataFrame:
    # BEGIN SOLUTION
    rows = [{"id": q["id"], "lang": q["lang"], "answerable": ok, "score": R.best_bm25(q["question"]), "question": q["question"]}
            for ok, group in ((True, YES), (False, NO)) for q in group]
    return pd.DataFrame(rows)
    # END SOLUTION


# %%
try:
    S = score_table()
except NotImplementedError:
    S = pd.DataFrame([{"id": q["id"], "lang": q["lang"], "answerable": ok, "score": R.best_bm25(q["question"]),
                       "question": q["question"]} for ok, g in ((True, YES), (False, NO)) for q in g])
print(S.groupby("answerable").score.describe()[["min", "25%", "50%", "75%", "max"]].round(1))
print(S[~S.answerable].sort_values("score", ascending=False).head(3)[["question", "score"]].to_string(index=False))
llm.check(S[S.answerable].score.median() > S[~S.answerable].score.median(), "answerable questions score higher")

# %% [markdown]
# 🔍 **Look at** · the highest-scoring unanswerable questions. They share words with real policies ("fine", "Central
# station", "night"), which is exactly why a model would answer them.

# %% [markdown]
# ## 2 · An abstention rule (6')
#
# Two signals, combined: abstain when the best score is below a threshold (the model is not even asked), or when the
# model replies `NOT_IN_CORPUS`.
#
# ✏️ **Exercise** · Write `model_says_no(q)`: retrieve 4 passages, ask the model with `SYSTEM`, return `True` if the reply
# contains `NOT_IN_CORPUS` or has no `[Pnn.n]` citation. Then write `abstain(q, threshold, said_no)` from the two signals,
# where `said_no` is the result of `model_says_no(q)`.

# %%
def model_says_no(q: str) -> bool:
    # BEGIN SOLUTION
    passages = "\n".join(f"[{c['ref']}] {c['text']}" for _, c in R.search(q, 4))
    reply = llm.text(llm.complete([{"role": "system", "content": SYSTEM},
                                   {"role": "user", "content": f"PASSAGES:\n{passages}\n\nQUESTION: {q}"}]))
    return "NOT_IN_CORPUS" in reply or not re.search(r"\[P\d+\.\d+\]", reply)
    # END SOLUTION


def abstain(score: float, threshold: float, said_no: bool) -> bool:
    # BEGIN SOLUTION
    return score < threshold or said_no
    # END SOLUTION


# %%
try:
    S["model_no"] = [model_says_no(q) for q in S.question]  # one model call per question, reused for every threshold
except NotImplementedError:
    S["model_no"] = ~S.answerable
print(pd.crosstab(S.answerable, S.model_no, rownames=["answerable"], colnames=["model says not in corpus"]))

# %% [markdown]
# ## 3 · Thresholds against both rates (7')
#
# Two rates matter: the **abstention rate** on unanswerable questions (higher is better) and the **false abstention
# rate** on answerable ones (lower is better). Raising the threshold moves both.
#
# ✏️ **Exercise** · Write `sweep(thresholds)`: for each threshold, both rates from `abstain(score, t, model_no)`.

# %%
def sweep(thresholds) -> pd.DataFrame:
    # BEGIN SOLUTION
    rows = []
    for t in thresholds:
        dec = [abstain(s, t, m) for s, m in zip(S.score, S.model_no)]
        S["_a"] = dec
        rows.append({"threshold": t, "abstention_rate": round(S[~S.answerable]._a.mean(), 2),
                     "false_abstention": round(S[S.answerable]._a.mean(), 2)})
    return pd.DataFrame(rows)
    # END SOLUTION


# %%
try:
    T = sweep([0, 4, 5, 6, 7, 8])
except NotImplementedError:
    T = pd.DataFrame({"threshold": [0, 7], "abstention_rate": [0.5, 0.8], "false_abstention": [0.07, 0.13]})
print(T.to_string(index=False))
llm.check(T.abstention_rate.is_monotonic_increasing, "a higher threshold never abstains less")

# %% [markdown]
# Choose the threshold Darb will use and say why: which error is worse for a rider, a wrong answer or a "please ask a
# person"? The reference assistant (`wasil.Wasil.ABSTAIN_BELOW`) uses 7.

# %% [markdown]
# ## 4 · What the rider reads (6')
#
# An abstention is an answer too. It says plainly that the policies do not cover the question, does not guess, offers a
# person, and is in the rider's language.
#
# ✏️ **Exercise** · Write `NOT_THERE`, a dict with an English and an Arabic message, and `reply_for(q)` that returns the
# message in the question's language (Arabic when it has more Arabic letters than Latin ones).

# %%
def make_reply():
    # BEGIN SOLUTION
    not_there = {"en": "I could not find this in Darb's published policies, so I will not guess. You can ask for a member "
                       "of staff in the app or through the contact centre.",
                 "ar": "لم أجد هذا في سياسات درب المنشورة، ولن أخمّن. يمكنك طلب التحدث إلى موظف عبر التطبيق أو مركز الاتصال."}

    def reply_for(q: str) -> str:
        ar = len(re.findall(r"[؀-ۿ]", q)) > len(re.findall(r"[A-Za-z]", q))
        return not_there["ar" if ar else "en"]
    return reply_for
    # END SOLUTION


# %%
try:
    reply_for = make_reply()
except NotImplementedError:
    import wasil
    reply_for = lambda q: wasil.ABSTAIN[wasil.lang_of(q)]
for q in (NO[0]["question"], NO[20]["question"]):
    print(q, "->", reply_for(q))
llm.check("staff" in reply_for(NO[0]["question"]) and "موظف" in reply_for(NO[20]["question"]),
          "both languages offer a person")
print(llm.LEDGER)

# %% [markdown]
# ## ✱ Stretch · A threshold per language

# %%
def stretch():
    # BEGIN SOLUTION
    for lang in ("en", "ar"):
        sub = S[S.lang == lang]
        for t in (5, 6, 7, 8):
            a = [abstain(s, t, m) for s, m in zip(sub.score, sub.model_no)]
            sub = sub.assign(_a=a)
            print(lang, t, "abstains on unanswerable", round(sub[~sub.answerable]._a.mean(), 2),
                  "| false abstention", round(sub[sub.answerable]._a.mean(), 2))
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why not rely on the model's NOT_IN_CORPUS alone?
# <details><summary>Answer</summary>A model given related passages tends to answer anyway; the score is a second signal
# that does not depend on the model's restraint.</details>
#
# 2. Raising the threshold from 6 to 8 catches more unanswerable questions. What does it cost?
# <details><summary>Answer</summary>More answerable questions are declined: riders who should have had an answer are
# sent to a person.</details>
#
# 3. Thirty unanswerable questions were written by the course. What does that leave out?
# <details><summary>Answer</summary>The questions real riders ask; collect declined questions in production and add
# them to the set.</details>
#
# **Carry forward.** `wasil.Wasil.grounded` combines both signals at threshold 7; Day 4 measures it in the evaluation set.
