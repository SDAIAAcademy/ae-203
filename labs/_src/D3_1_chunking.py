# %% [markdown]
# # Lab 3.1 · Two chunkings of the policy corpus
#
# Day 3 · Session 1 (Chunking and indexing a policy corpus) · 25 min.
#
# Wasil will answer from Darb's 120 policy pages (60 policies in English and Arabic). Before searching, the pages are cut
# into chunks and indexed. You normalise Arabic, cut the corpus two ways (by section and by fixed windows), and index
# both in SQLite's full-text search to see what each returns. No model call in this lab.
#
# **Reference state.** `data/policies/*.md` and `darb.pages()`, which reads them with their sections.
#
# **Tasks**
# - [ ] 1 · Load the pages and normalise Arabic (6')
# - [ ] 2 · Chunk by section (6')
# - [ ] 3 · Chunk by fixed windows with overlap (7')
# - [ ] 4 · Index both in SQLite full-text search (6')
# - [ ] ✱ Stretch · Window sizes against chunk counts

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
else:
    while not Path("_tools").exists() and Path.cwd() != Path.cwd().parent:
        os.chdir("..")  # solutions/ notebooks run from labs/
sys.path.insert(0, os.getcwd())

import re
import sqlite3
import statistics

import llm
import darb as D

PAGES = D.pages()
print(len(PAGES), "pages |", sum(p["lang"] == "ar" for p in PAGES), "in Arabic |",
      [p["page"] for p in PAGES if p["status"] == "superseded"], "superseded")
print(PAGES[2]["text"][:400])
try:
    sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE t USING fts5(x)")
    print("SQLite", sqlite3.sqlite_version, "with FTS5")
except sqlite3.OperationalError:
    print("This Python's SQLite has no FTS5: in step 4 use D.BM25 instead")

# %% [markdown]
# ## 1 · Load the pages and normalise Arabic (6')
#
# The same Arabic word is written several ways: with or without diacritics, with different forms of alef, with taa
# marbuta or haa at the end, with Arabic-Indic or Western digits. A search that does not unify them misses matches.
#
# ✏️ **Exercise** · Write `normalise(text)`: remove diacritics (U+064B to U+0652) and tatweel (U+0640); turn أ إ آ into
# ا, ة into ه, ى into ي; turn Arabic-Indic digits into Western ones; lower-case the rest.

# %%
def normalise(text: str) -> str:
    # BEGIN SOLUTION
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    text = re.sub(r"[ً-ْـ]", "", text)
    text = re.sub("[أإآ]", "ا", text).replace("ة", "ه").replace("ى", "ي")
    return text.lower()
    # END SOLUTION


# %%
PAIRS = [("الأُجْرَة", "الاجره"), ("إلغاء", "الغاء"), ("الحافلة ٢٧", "الحافله 27"), ("Refund", "refund")]
try:
    got = [normalise(a) for a, _ in PAIRS]
except NotImplementedError:
    got = [D.normalise(a) for a, _ in PAIRS]
for (a, b), g in zip(PAIRS, got):
    print(f"{a:14} -> {g:14} {'✅' if g == b else '❌ expected ' + b}")
llm.check(all(g == b for (_, b), g in zip(PAIRS, got)), "four spellings unified")

# %% [markdown]
# ## 2 · Chunk by section (6')
#
# Darb's pages have numbered sections (`P03.1`). A section is one rule: the natural unit to retrieve and to cite.
#
# ✏️ **Exercise** · Write `by_section(pages)`: one chunk per section, a dict with `ref` (`P03.1`), `page`
# (`P03_en`), `lang`, `status` and `text` = page title + ". " + heading + ". " + section text, so a chunk stands alone.

# %%
def by_section(pages: list[dict]) -> list[dict]:
    # BEGIN SOLUTION
    return [{"ref": s["ref"], "page": p["page"], "lang": p["lang"], "status": p["status"],
             "text": f"{p['title']}. {s['heading']}. {s['text']}"} for p in pages for s in p["sections"]]
    # END SOLUTION


# %%
try:
    SECTIONS = by_section(PAGES)
except NotImplementedError:
    SECTIONS = D.chunk_by_section(PAGES)
print(len(SECTIONS), "section chunks, mean", round(statistics.mean(len(c["text"]) for c in SECTIONS)), "characters")
print(SECTIONS[6])
llm.check(len(SECTIONS) == 272, "272 sections across the 120 pages")

# %% [markdown]
# ## 3 · Chunk by fixed windows with overlap (7')
#
# Many corpora have no sections. The usual fallback is a window of N characters (or tokens) that slides with some
# overlap, so a sentence cut at one edge appears whole in the next window.
#
# ✏️ **Exercise** · Write `by_window(pages, size=300, overlap=50)`: windows over each page's whole text, starting every
# `size - overlap` characters. Keep `page`, `lang`, `status`, and set `ref` to the last section heading that starts
# inside or before the window (search `## P..` in the text up to the window's end).

# %%
def by_window(pages: list[dict], size: int = 300, overlap: int = 50) -> list[dict]:
    # BEGIN SOLUTION
    out = []
    for p in pages:
        body = p["text"]
        for start in range(0, max(1, len(body) - overlap), size - overlap):
            refs = re.findall(r"## (P\d+\.\d+)", body[:start + size])
            out.append({"ref": refs[-1] if refs else p["id"] + ".1", "page": p["page"], "lang": p["lang"],
                        "status": p["status"], "text": body[start:start + size]})
    return out
    # END SOLUTION


# %%
try:
    WINDOWS = by_window(PAGES)
except NotImplementedError:
    WINDOWS = D.chunk_fixed(PAGES)
cut = sum(1 for c in WINDOWS if not re.search(r"[.!?؟\s]$", c["text"]))
print(len(WINDOWS), "windows |", cut, "end in the middle of a word or sentence")
print(repr(WINDOWS[1]["text"][-80:]))
llm.check(len(WINDOWS) < len(SECTIONS), "fewer, longer chunks; each may hold several rules")

# %% [markdown]
# 🔍 **Look at** · a window whose `ref` is one section but whose text holds the end of the previous one. A citation of
# that window would point at the wrong rule.

# %% [markdown]
# ## 4 · Index both in SQLite full-text search (6')
#
# SQLite's FTS5 is a full-text index in the standard library, with a BM25 ranking built in. Index the **normalised**
# text, and normalise the query the same way.
#
# ✏️ **Exercise** · Write `index(chunks)` that creates an in-memory FTS5 table `chunks(ref, page, body)` and inserts
# every chunk with `normalise(text)`; and `query(db, q, k=3)` that returns the top `k` rows `(ref, page)` ordered by
# `bm25(chunks)`, with the query's words joined by OR.

# %%
def index(chunks: list[dict]) -> sqlite3.Connection:
    # BEGIN SOLUTION
    db = sqlite3.connect(":memory:")
    db.execute("CREATE VIRTUAL TABLE chunks USING fts5(ref, page, body)")
    db.executemany("INSERT INTO chunks VALUES (?, ?, ?)", [(c["ref"], c["page"], D.normalise(c["text"])) for c in chunks])
    return db
    # END SOLUTION


def query(db: sqlite3.Connection, q: str, k: int = 3) -> list[tuple]:
    # BEGIN SOLUTION
    words = [w for w in re.findall(r"\w+", D.normalise(q)) if w not in D.STOP]
    sql = "SELECT ref, page FROM chunks WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT ?"
    return db.execute(sql, (" OR ".join(f'"{w}"' for w in words), k)).fetchall()
    # END SOLUTION


# %%
QUESTIONS = ["How many days do I have to claim a delay refund?", "كم غرامة الأكل داخل القطار؟",
             "Can I take a full-size bicycle on the metro?"]
try:
    dbs = {"sections": index(SECTIONS), "windows": index(WINDOWS)}
    for q in QUESTIONS:
        print(q)
        for name, db in dbs.items():
            print(f"   {name:9}", query(db, q))
    top = query(dbs["sections"], QUESTIONS[0], 1)[0][0]
except NotImplementedError:
    top = "P03.2"
    print("index and query not written yet")
llm.check(top in ("P03.2", "P31.2"), f"the refund-claim question finds a claim section ({top})")

# %% [markdown]
# 🔍 **Look at** · the first question's results. The superseded page P31 ("claims were made within 7 days") competes
# with P03 ("within 14 days"). Nothing in the index knows which is in force: Lab 3.3 deals with that.

# %% [markdown]
# ## ✱ Stretch · Window sizes against chunk counts

# %%
def stretch():
    # BEGIN SOLUTION
    for size in (150, 300, 600):
        w = by_window(PAGES, size, size // 6)
        print(size, "characters:", len(w), "chunks, mean", round(statistics.mean(len(c["text"]) for c in w)))
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why normalise the query as well as the index?
# <details><summary>Answer</summary>Matching compares the two; a normalised index and a raw query still differ on
# alef forms and taa marbuta.</details>
#
# 2. Why put the page title in front of each section chunk?
# <details><summary>Answer</summary>A section such as "How to claim" means nothing alone; the title says it is about
# delay refunds.</details>
#
# 3. When would fixed windows be the better choice?
# <details><summary>Answer</summary>When documents have no reliable structure, such as scanned letters or long free
# text.</details>
#
# **Carry forward.** `darb.chunk_by_section` and `darb.normalise` are the reference versions; Lab 3.2 searches the section
# chunks.
