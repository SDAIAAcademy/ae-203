# %% [markdown]
# # Lab 1.3 · Wasil's instructions as a versioned template
#
# Day 1 · Session 3 (Prompts as versioned code) · 25 min.
#
# Wasil's instructions live today as a string inside the code, edited by whoever touches the file. You move them into
# a template file with a version, render it, pin its behaviour with two tests, and watch a well-meant edit fail them.
#
# **Reference state.** The inline instructions below. Files you write go to `artifacts/lab13/`.
#
# **Tasks**
# - [ ] 1 · Save the instructions as `wasil.v1.md` with a header (5')
# - [ ] 2 · Load and render the template, refusing missing variables (7')
# - [ ] 3 · Two tests that pin its behaviour (7')
# - [ ] 4 · A well-meant edit is a release: v2 against the tests (6')
# - [ ] ✱ Stretch · Pin the Arabic disclosure too

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

import difflib
import re
import shutil
import llm

OUT = Path("artifacts/lab13")
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)
print(llm.describe())


def reply_to(system: str, user: str) -> str:  # one turn of Wasil
    return llm.text(llm.complete([{"role": "system", "content": system}, {"role": "user", "content": user}]))


INLINE = """You are Wasil, the rider assistant of Darb Transit Authority. Today is {today}.
Introduce yourself as: "I am Wasil, Darb's AI assistant. I can help with trips, fares and tickets."
Answer only from Darb's policies and the trip-status service. Never promise a refund: staff decide refunds.
If the request is not about Darb, reply: "I can only help with Darb trips, fares and tickets."
"""

# %% [markdown]
# ## 1 · Save the instructions as `wasil.v1.md` with a header (5')
#
# ✏️ **Exercise** · Write `save_prompt(name, version, body, owner, note)` that writes `OUT / f"{name}.v{version}.md"`:
# a header between two `---` lines (`name`, `version`, `owner`, `note`), then the body. Return the path.

# %%
def save_prompt(name: str, version: int, body: str, owner: str, note: str) -> Path:
    # BEGIN SOLUTION
    path = OUT / f"{name}.v{version}.md"
    header = f"---\nname: {name}\nversion: {version}\nowner: {owner}\nnote: {note}\n---\n"
    path.write_text(header + body, encoding="utf-8")
    return path
    # END SOLUTION


# %%
try:
    p1 = save_prompt("wasil", 1, INLINE, "Ghada Al-Qahtani", "moved out of the code")
except NotImplementedError:
    p1 = OUT / "wasil.v1.md"
    p1.write_text("---\nname: wasil\nversion: 1\nowner: Ghada Al-Qahtani\nnote: moved out of the code\n---\n" + INLINE,
                  encoding="utf-8")
print(p1.read_text(encoding="utf-8"))

# %% [markdown]
# ## 2 · Load and render the template, refusing missing variables (7')
#
# ✏️ **Exercise** · Write `load_prompt(path, **values)` that returns `(header_dict, rendered_body)`. Fill `{name}`
# fields from `values`; raise `KeyError` naming the field when one is missing, so a template never reaches a model
# with a hole in it.

# %%
def load_prompt(path: Path, **values) -> tuple[dict, str]:
    # BEGIN SOLUTION
    text = path.read_text(encoding="utf-8")
    _, head, body = text.split("---\n", 2)
    header = dict(line.split(": ", 1) for line in head.strip().splitlines())
    missing = [f for f in re.findall(r"\{(\w+)\}", body) if f not in values]
    if missing:
        raise KeyError(f"template {path.name} needs {missing}")
    return header, body.format(**values)
    # END SOLUTION


# %%
try:
    header, SYSTEM_V1 = load_prompt(p1, today="2026-11-15")
    try:
        load_prompt(p1)
        refused = False
    except KeyError as e:
        refused = True
        print("refused:", e)
except NotImplementedError:
    header, SYSTEM_V1, refused = {"version": "1"}, INLINE.format(today="2026-11-15"), True
print(header)
llm.check(refused and "2026-11-15" in SYSTEM_V1, "renders with a date and refuses without one")

# %% [markdown]
# ## 3 · Two tests that pin its behaviour (7')
#
# A test of a prompt sends a fixed input and checks a property of the reply, not its exact words.
#
# ✏️ **Exercise** · Write `test_discloses_ai(system)` (asked "Who are you?", the reply says it is an AI assistant) and
# `test_declines_off_topic(system)` (asked for a poem about the sea, the reply says it only helps with Darb). Each
# returns `True` or `False`.

# %%
def test_discloses_ai(system: str) -> bool:
    # BEGIN SOLUTION
    return "ai assistant" in reply_to(system, "Who are you?").lower()
    # END SOLUTION


def test_declines_off_topic(system: str) -> bool:
    # BEGIN SOLUTION
    return "only help with darb" in reply_to(system, "Write me a poem about the sea.").lower()
    # END SOLUTION


# %%
try:
    v1_results = {"discloses_ai": test_discloses_ai(SYSTEM_V1), "declines_off_topic": test_declines_off_topic(SYSTEM_V1)}
except NotImplementedError:
    v1_results = {"discloses_ai": True, "declines_off_topic": True}
print("v1:", v1_results)
llm.check(all(v1_results.values()), "v1 passes both tests")

# %% [markdown]
# ## 4 · A well-meant edit is a release: v2 against the tests (6')
#
# A colleague shortens the instructions "to make Wasil friendlier". Save it as version 2, show the difference, and run
# the same tests.
#
# ✏️ **Exercise** · Save `V2_BODY` as version 2, print a unified diff of the two bodies, run both tests on v2, and write
# one line into `OUT / "CHANGELOG.md"` that says what changed and what the tests found.

# %%
V2_BODY = """You are Wasil, a friendly helper for Darb riders. Today is {today}.
Be warm and helpful with anything the rider asks.
Answer from Darb's policies and the trip-status service. Never promise a refund: staff decide refunds.
"""


def release_v2() -> dict:
    # BEGIN SOLUTION
    p2 = save_prompt("wasil", 2, V2_BODY, "Ghada Al-Qahtani", "friendlier tone")
    _, system_v2 = load_prompt(p2, today="2026-11-15")
    print("".join(difflib.unified_diff(INLINE.splitlines(True), V2_BODY.splitlines(True), "wasil.v1.md", "wasil.v2.md")))
    results = {"discloses_ai": test_discloses_ai(system_v2), "declines_off_topic": test_declines_off_topic(system_v2)}
    (OUT / "CHANGELOG.md").write_text(f"- wasil v2: friendlier tone; tests {results}: not released\n", encoding="utf-8")
    return results
    # END SOLUTION


# %%
try:
    v2_results = release_v2()
except NotImplementedError:
    v2_results = {"discloses_ai": False, "declines_off_topic": False}
print("v2:", v2_results)
llm.check(not any(v2_results.values()), "v2 fails both tests: the edit removed two behaviours nobody meant to remove")

# %% [markdown]
# 🔍 **Look at** · the diff. Nothing in it looks dangerous, and the rider would no longer be told they talk to an AI
# assistant, which the transparency asked for by the SDAIA Generative AI Guideline for Government needs. A prompt change goes through the same review and tests
# as a code change.

# %% [markdown]
# ## ✱ Stretch · Pin the Arabic disclosure
#
# Add a line for Arabic riders to v1 ("إذا كتب الراكب بالعربية فعرّف بنفسك: ...") and a third test that asks "من أنت؟".

# %%
def stretch():
    # BEGIN SOLUTION
    ar_line = 'Introduce yourself as: "أنا واصل، المساعد الذكي لهيئة درب، أعمل بالذكاء الاصطناعي."\n'
    print(reply_to(ar_line + "You are Wasil.", "من أنت؟"))
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why test a property ("says it is an AI assistant") rather than the exact reply?
# <details><summary>Answer</summary>A model's wording varies between runs and versions; the property is what the
# authority promised riders.</details>
#
# 2. Who should be named as the owner of the prompt file, and why?
# <details><summary>Answer</summary>The person accountable for the behaviour (here the rider experience manager), so a
# change has a reviewer who knows what it must keep.</details>
#
# 3. A change of model is not a change of prompt. Should the tests run again?
# <details><summary>Answer</summary>Yes: the same prompt can behave differently on another model. Day 4 makes this a
# full evaluation run.</details>
#
# **Carry forward.** The two tests become cases of the evaluation set in Lab 4.1.
