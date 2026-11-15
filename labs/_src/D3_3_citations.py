# %% [markdown]
# # Lab 3.3 · Answers with checked citations
#
# Day 3 · Session 3 (Answers with citations) · 25 min.
#
# Wasil answers a policy question from retrieved passages and cites the section it used, such as `[P03.1]`. A
# citation is only worth something if it is checked, so you write the checker: does the cited section exist, was it
# among the passages, is it in force, and does it contain the fact the answer needs?
#
# **Reference state.** `darb.Retriever` (the hybrid search of Lab 3.2) over all section chunks, including the superseded
# page P31, and the 30 answerable questions with their source section.
#
# **Tasks**
# - [ ] 1 · Passages with identifiers in the prompt (6')
# - [ ] 2 · Answer and collect citations (7')
# - [ ] 3 · A citation checker (6')
# - [ ] 4 · Thirty questions, and the superseded page (6')
# - [ ] ✱ Stretch · Answer Arabic questions in Arabic

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

import re
import pandas as pd

import llm
import darb as D

ALL = D.Retriever(include_superseded=True)
SECTIONS = {c["ref"] + "_" + c["lang"]: c for c in D.chunk_by_section(D.pages())}
STATUS = {c["ref"]: c["status"] for c in SECTIONS.values()}
QS = D.load_jsonl("questions/answerable.jsonl")
print(llm.describe(), "|", len(QS), "questions")
SYSTEM = ("Answer the rider's question only from the passages. Cite the passage id in square brackets, like [P03.1]. "
          "If the passages do not hold the answer, reply exactly NOT_IN_CORPUS.")

# %% [markdown]
# ## 1 · Passages with identifiers in the prompt (6')
#
# ✏️ **Exercise** · Write `build_messages(question, hits)` that returns the two messages: `SYSTEM`, and a user message with
# `PASSAGES:` followed by one line per hit, `[ref] text`, then a blank line and `QUESTION: ` with the question.

# %%
def build_messages(question: str, hits: list) -> list[dict]:
    # BEGIN SOLUTION
    passages = "\n".join(f"[{c['ref']}] {c['text']}" for _, c in hits)
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"PASSAGES:\n{passages}\n\nQUESTION: {question}"}]
    # END SOLUTION


# %%
q = QS[5]["question"]
hits = ALL.search(q, 4)
try:
    msgs = build_messages(q, hits)
except NotImplementedError:
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "PASSAGES:\n" + "\n".join(
        f"[{c['ref']}] {c['text']}" for _, c in hits) + f"\n\nQUESTION: {q}"}]
print(msgs[1]["content"])
llm.check(msgs[1]["content"].count("[P") == 4, "four passages, each with its identifier")

# %% [markdown]
# ## 2 · Answer and collect citations (7')
#
# ✏️ **Exercise** · Write `answer(question, retriever, k=4)` that retrieves `k` hits, calls the model with
# `build_messages`, and returns `(text, citations, hits)`, the citations being every `[Pnn.n]` in the text.

# %%
def answer(question: str, retriever, k: int = 4) -> tuple[str, list[str], list]:
    # BEGIN SOLUTION
    hits = retriever.search(question, k)
    text = llm.text(llm.complete(build_messages(question, hits))).strip()
    return text, re.findall(r"\[(P\d+\.\d+)\]", text), hits
    # END SOLUTION


# %%
try:
    text, cites, used = answer(q, ALL)
except NotImplementedError:
    text, cites, used = "Claims are made within 14 days of the journey. [P03.2]", ["P03.2"], hits
print(q, "\n->", text, cites)

# %% [markdown]
# ## 3 · A citation checker (6')
#
# This is the automatic check LO4 asks for.
#
# ✏️ **Exercise** · Write `check(text, cites, hits, must_contain)` that returns a dict of booleans: `cited` (at least one
# citation), `exists` (every cited ref is a section of the corpus), `given` (every cited ref was among the passages),
# `in_force` (no cited section is superseded) and `supports` (`must_contain` appears in the answer and in the text of a
# cited passage).

# %%
def check(text: str, cites: list[str], hits: list, must_contain: str) -> dict:
    # BEGIN SOLUTION
    given = {c["ref"]: c["text"] for _, c in hits}
    return {"cited": bool(cites), "exists": bool(cites) and all(r in STATUS for r in cites),
            "given": bool(cites) and all(r in given for r in cites),
            "in_force": bool(cites) and all(STATUS.get(r) == "in force" for r in cites),
            "supports": must_contain.lower() in text.lower()
                        and any(must_contain.lower() in given.get(r, "").lower() for r in cites)}
    # END SOLUTION


# %%
FAKE = ("A single fare is SAR 5. [P01.9]", ["P01.9"])
try:
    print(check(text, cites, used, QS[5]["must_contain"]))
    bad = check(*FAKE, used, "5")
    print("an invented citation:", bad)
    ok = not bad["exists"] and not bad["supports"]
except NotImplementedError:
    ok = True
llm.check(ok, "an invented section is caught")

# %% [markdown]
# ## 4 · Thirty questions, and the superseded page (6')
#
# ✏️ **Exercise** · Write `run(retriever)`: for each question, `answer` and `check` (with the question's `must_contain`),
# and also record whether the cited section is the question's `source`. Return a DataFrame. Run it on `ALL`, then on a
# retriever that leaves superseded pages out, and compare.

# %%
def run(retriever) -> pd.DataFrame:
    rows = []
    for item in QS:
        # BEGIN SOLUTION
        text, cites, hits = answer(item["question"], retriever)
        rows.append({"id": item["id"], "lang": item["lang"], **check(text, cites, hits, item["must_contain"]),
                     "right_section": item["source"] in cites, "cites": ",".join(cites), "answer": text[:70]})
        # END SOLUTION
    return pd.DataFrame(rows)


# %%
try:
    before = run(ALL)
    after = run(D.Retriever(include_superseded=False))
    cols = ["cited", "exists", "given", "in_force", "supports", "right_section"]
    print(pd.DataFrame({"with P31": before[cols].mean(), "without P31": after[cols].mean()}).round(2).to_string())
    print("\ncited a superseded section:", before[~before.in_force & before.cited][["id", "cites", "answer"]].to_string(index=False))
    print("\nfailures after the fix:")
    print(after[~(after.supports & after.in_force)][["id", "lang", "cites", "answer"]].to_string(index=False))
    llm.check(after.in_force.sum() >= before.in_force.sum(), "leaving superseded pages out never adds a superseded citation")
except NotImplementedError:
    print("run not written yet")
print(llm.LEDGER)

# %% [markdown]
# 🔍 **Look at** · any answer whose passages included P30. That page carries a planted instruction for "automated
# assistants", and a model that obeys it writes an answer with no citation. The checker catches the missing citation;
# Day 4 removes the instruction before the model sees it.

# %% [markdown]
# ## ✱ Stretch · Answer Arabic questions in Arabic
#
# Add "Answer in the language of the question." to the system prompt and check that the ten Arabic answers contain Arabic
# letters.

# %%
def stretch():
    # BEGIN SOLUTION
    global SYSTEM
    old = SYSTEM
    SYSTEM = old + " Answer in the language of the question."
    arabic = [x for x in QS if x["lang"] == "ar"]
    n = sum(bool(re.search(r"[؀-ۿ]", answer(x["question"], ALL)[0])) for x in arabic)
    SYSTEM = old
    print(n, "of", len(arabic), "Arabic questions answered in Arabic")
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. A cited section exists and was among the passages, but does not contain the figure in the answer. What is wrong?
# <details><summary>Answer</summary>The answer is not supported by its citation: the model took the figure from
# elsewhere or invented it.</details>
#
# 2. Where does the protection against the superseded page belong: the prompt, the index or the checker?
# <details><summary>Answer</summary>The index (leave it out, or rank it down) and the checker (reject it); a sentence in
# the prompt is a request, not a guarantee.</details>
#
# 3. Why use stable section identifiers rather than "passage 2"?
# <details><summary>Answer</summary>They survive re-ranking and re-indexing, and a rider or a member of staff can open
# the section.</details>
#
# **Carry forward.** `wasil.Wasil.grounded` does this, with superseded pages left out and the citations checked.
