# %% [markdown]
# # Lab 3.2 · Keyword, vector and hybrid search
#
# Day 3 · Session 2 (Lexical, dense and hybrid search) · 25 min.
#
# Thirty rider questions, twenty in English and ten in Arabic, each with the section that answers it. You measure search
# before choosing one: BM25 keyword search, vector search, and the two fused, by language. No model call in this lab.
#
# **Reference state.** The 272 section chunks of Lab 3.1 (`darb.chunk_by_section`) and
# `data/questions/answerable.jsonl`.
#
# **Tasks**
# - [ ] 1 · An evaluation of search: hit at k and MRR (6')
# - [ ] 2 · Keyword search with BM25 (6')
# - [ ] 3 · Vectors and the hybrid with RRF (7')
# - [ ] 4 · By language, and the misses (6')
# - [ ] ✱ Stretch · Weight one ranking more than the other

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
else:
    while not Path("_tools").exists() and Path.cwd() != Path.cwd().parent:
        os.chdir("..")  # solutions/ notebooks run from labs/
sys.path.insert(0, os.getcwd())

from collections import Counter

import pandas as pd
from rank_bm25 import BM25Okapi

import llm
import darb as D

CHUNKS = D.chunk_by_section(D.pages())
QS = D.load_jsonl("questions/answerable.jsonl")
print(len(CHUNKS), "chunks |", len(QS), "questions, e.g.", QS[0])

# %% [markdown]
# ## 1 · An evaluation of search: hit at k and MRR (6')
#
# A search is a function `search(question, k)` that returns `[(score, chunk), ...]`. A question is a hit at k when its
# source section (`source`, such as `P01.1`) is among the top k results. The reciprocal rank is 1 / the rank of the first
# right result (0 if absent); MRR is its mean.
#
# ✏️ **Exercise** · Write `evaluate(search, questions)` that returns a dict with `hit@1`, `hit@5` and `mrr`, rounded to
# two decimals.

# %%
def evaluate(search, questions: list[dict]) -> dict:
    # BEGIN SOLUTION
    h1 = h5 = rr = 0.0
    for q in questions:
        refs = [c["ref"] for _, c in search(q["question"], 5)]
        h1 += refs[:1] == [q["source"]]
        h5 += q["source"] in refs
        rr += 1 / (refs.index(q["source"]) + 1) if q["source"] in refs else 0
    n = len(questions)
    return {"hit@1": round(h1 / n, 2), "hit@5": round(h5 / n, 2), "mrr": round(rr / n, 2)}
    # END SOLUTION


# %%
def first_chunks(question, k):  # a deliberately bad search, to test the evaluation
    return [(0.0, c) for c in CHUNKS[:k]]


try:
    base = evaluate(first_chunks, QS)
except NotImplementedError:
    base = {"hit@1": 0.03, "hit@5": 0.1, "mrr": 0.05}
print("first five chunks, whatever the question:", base)
llm.check(base["hit@5"] < 0.2, "a search that ignores the question scores near zero")

# %% [markdown]
# ## 2 · Keyword search with BM25 (6')
#
# BM25 scores a chunk by the query words it contains: rare words count more, repeated words count less and less, long
# chunks are not favoured. Tokenise both sides with `D.tokens` (normalised words without stop words).
#
# ✏️ **Exercise** · Write `make_bm25(chunks)` that builds a `BM25Okapi` index over the chunks' tokens and returns a
# `search(question, k)` function.

# %%
def make_bm25(chunks: list[dict]):
    # BEGIN SOLUTION
    index = BM25Okapi([D.tokens(c["text"]) or ["_"] for c in chunks])

    def search(question: str, k: int = 5):
        scores = index.get_scores(D.tokens(question))
        top = sorted(range(len(chunks)), key=lambda i: -scores[i])[:k]
        return [(float(scores[i]), chunks[i]) for i in top]
    return search
    # END SOLUTION


# %%
try:
    bm25 = make_bm25(CHUNKS)
except NotImplementedError:
    bm25 = D.BM25(CHUNKS).search
try:
    print("BM25:", evaluate(bm25, QS))
except NotImplementedError:
    pass
print([c["ref"] for _, c in bm25(QS[4]["question"], 3)], "for", QS[4]["question"])

# %% [markdown]
# ## 3 · Vectors and the hybrid with RRF (7')
#
# `D.Vectors` turns each chunk into a vector of character 3- to 5-gram weights and ranks by cosine similarity. It matches
# parts of words ("refund" in "refunded", "الاسترداد" in "استرداد"), which keyword search misses. Learned embeddings
# from a model do the same with meaning; these are computed on the laptop, with no model download.
#
# Reciprocal rank fusion (RRF) merges two rankings: each list adds `1 / (60 + rank)` to a chunk's score.
#
# ✏️ **Exercise** · Write `make_hybrid(search_a, search_b, depth=20)` that returns a search fusing the top `depth`
# results of both with RRF.

# %%
vec = D.Vectors(CHUNKS).search


def make_hybrid(search_a, search_b, depth: int = 20):
    # BEGIN SOLUTION
    def search(question: str, k: int = 5):
        score, keep = Counter(), {}
        for ranking in (search_a(question, depth), search_b(question, depth)):
            for rank, (_, c) in enumerate(ranking, 1):
                score[c["chunk"]] += 1 / (60 + rank)
                keep[c["chunk"]] = c
        return [(s, keep[cid]) for cid, s in score.most_common(k)]
    return search
    # END SOLUTION


# %%
try:
    hybrid = make_hybrid(bm25, vec)
except NotImplementedError:
    hybrid = lambda q, k=5: D.rrf(bm25(q, 20), vec(q, 20), top=k)
try:
    table = pd.DataFrame({name: evaluate(fn, QS) for name, fn in [("bm25", bm25), ("vectors", vec), ("hybrid", hybrid)]}).T
except NotImplementedError:
    table = pd.DataFrame({"hit@1": [0.9, 0.9, 0.93]}, index=["bm25", "vectors", "hybrid"])
print(table.to_string())
llm.check(table.loc["hybrid", "hit@1"] >= min(table.loc["bm25", "hit@1"], table.loc["vectors", "hit@1"]),
          "the hybrid is at least as good as the weaker of the two")

# %% [markdown]
# ## 4 · By language, and the misses (6')
#
# ✏️ **Exercise** · Write `misses(search)` that returns one row per question where the source is not the top result:
# the question's id, language, the source and the top result's ref. Then compare hit@1 by language for the three
# searches.

# %%
def misses(search) -> pd.DataFrame:
    # BEGIN SOLUTION
    rows = []
    for q in QS:
        top = search(q["question"], 1)[0][1]["ref"]
        if top != q["source"]:
            rows.append({"id": q["id"], "lang": q["lang"], "source": q["source"], "top": top, "question": q["question"][:60]})
    return pd.DataFrame(rows)
    # END SOLUTION


# %%
try:
    for name, fn in [("bm25", bm25), ("vectors", vec), ("hybrid", hybrid)]:
        by = {lang: evaluate(fn, [q for q in QS if q["lang"] == lang])["hit@1"] for lang in ("en", "ar")}
        print(f"{name:8} hit@1 English {by['en']:.2f} | Arabic {by['ar']:.2f}")
    print(misses(hybrid).to_string(index=False))
except NotImplementedError:
    print("misses not written yet")

# %% [markdown]
# 🔍 **Look at** · each miss. Is the top result the superseded P31, a page in the other language, or a section of the
# same page? Each points at a different fix: status, language filter, or chunking.

# %% [markdown]
# ## ✱ Stretch · Weight one ranking more than the other

# %%
def stretch():
    # BEGIN SOLUTION
    for w in (0.5, 1.0, 2.0):
        def weighted(q, k=5, w=w):
            score, keep = Counter(), {}
            for weight, ranking in ((w, bm25(q, 20)), (1.0, vec(q, 20))):
                for rank, (_, c) in enumerate(ranking, 1):
                    score[c["chunk"]] += weight / (60 + rank)
                    keep[c["chunk"]] = c
            return [(s, keep[cid]) for cid, s in score.most_common(k)]
        print("BM25 weight", w, evaluate(weighted, QS))
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why measure on questions with known source sections before choosing a search?
# <details><summary>Answer</summary>Without them, "it looks better" is the only measure; with them, a change has a
# number.</details>
#
# 2. Keyword search misses "refunded" for "refund". Which search catches it, and why?
# <details><summary>Answer</summary>The character n-gram vectors, which share most of their pieces; learned
# embeddings would too.</details>
#
# 3. Thirty questions is a small set. What does one question change in hit@1?
# <details><summary>Answer</summary>About 0.03: differences of one or two questions are noise.</details>
#
# **Carry forward.** `darb.Retriever` is this hybrid over the section chunks; Lab 3.3 hands its passages to the model.
