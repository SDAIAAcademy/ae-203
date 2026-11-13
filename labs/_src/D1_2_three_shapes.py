# %% [markdown]
# # Lab 1.2 · One request, three shapes, one client
#
# Day 1 · Session 2 (Three API shapes, one interface) · 25 min.
#
# The same question to Wasil ("Was the Red Line late yesterday?", with one tool) is written for the three main API
# shapes: Chat Completions, Responses and Messages. You read where each shape puts the same things, fill the
# comparison table, then send one request to a hosted and to a local endpoint through one client.
#
# **Reference state.** Recorded requests and responses in `data/reference/shapes.json` and the reference table in
# `data/reference/comparison.json` (open it only to check yourself in step 3). The local endpoint is the course's
# stand-in server started in this notebook; nothing downloads a model.
#
# **Tasks**
# - [ ] 1 · Read the tool call out of each shape (6')
# - [ ] 2 · Read the usage out of each shape (6')
# - [ ] 3 · Fill the comparison table and check it (6')
# - [ ] 4 · The same call to a hosted and a local endpoint (7')
# - [ ] ✱ Stretch · Send the Responses shape to a provider that serves it

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
import pandas as pd
import llm
import darb as D

SHAPES = json.loads((D.DATA / "reference" / "shapes.json").read_text(encoding="utf-8"))
print(llm.describe())
print(list(SHAPES), "| keys of the Messages response:", list(SHAPES["messages"]["response"]))

# %% [markdown]
# ## 1 · Read the tool call out of each shape (6')
#
# ✏️ **Exercise** · Write `tool_call_of(shape, response)` that returns `(name, arguments_as_dict)` for each shape.
# Watch for where the call sits, and whether the arguments are a JSON string or an object.

# %%
def tool_call_of(shape: str, r: dict) -> tuple[str, dict]:
    # BEGIN SOLUTION
    if shape == "chat_completions":
        fn = r["choices"][0]["message"]["tool_calls"][0]["function"]
        return fn["name"], json.loads(fn["arguments"])
    if shape == "responses":
        item = next(i for i in r["output"] if i["type"] == "function_call")
        return item["name"], json.loads(item["arguments"])
    block = next(b for b in r["content"] if b["type"] == "tool_use")
    return block["name"], block["input"]
    # END SOLUTION


# %%
try:
    calls = {s: tool_call_of(s, SHAPES[s]["response"]) for s in SHAPES}
except NotImplementedError:
    calls = {s: ("get_trip_status", {"route": "M1", "date": "2026-11-14"}) for s in SHAPES}
for s, c in calls.items():
    print(f"{s:17} {c}")
llm.check(len({json.dumps(c, sort_keys=True) for c in calls.values()}) == 1, "the three shapes carry the same call")

# %% [markdown]
# ## 2 · Read the usage out of each shape (6')
#
# ✏️ **Exercise** · Write `usage_of(shape, response)` that returns `(input_tokens, output_tokens)`. Then look at
# which shape reports a total and which does not.

# %%
def usage_of(shape: str, r: dict) -> tuple[int, int]:
    # BEGIN SOLUTION
    u = r["usage"]
    if shape == "chat_completions":
        return u["prompt_tokens"], u["completion_tokens"]
    return u["input_tokens"], u["output_tokens"]
    # END SOLUTION


# %%
try:
    usage = {s: usage_of(s, SHAPES[s]["response"]) for s in SHAPES}
except NotImplementedError:
    usage = {s: (118, 24) for s in SHAPES}
print(usage)
llm.check(len(set(usage.values())) == 1, "same tokens, three spellings of the field names")

# %% [markdown]
# ## 3 · Fill the comparison table and check it (6')
#
# ✏️ **Exercise** · Fill one short cell per aspect and shape, from what you read in `SHAPES` (requests, responses and
# the `tool_result` each shape sends back). The check compares the field names you wrote with the reference table.

# %%
ASPECTS = ["system instructions", "user turn", "tool definition", "tool call in the reply", "tool result sent back",
           "why it stopped", "usage"]
def my_table() -> dict:
    # BEGIN SOLUTION
    return {
    "system instructions": ["message with role system", "instructions field", "top-level system field"],
    "user turn": ["messages, role user", "input string or items", "messages, role user, content blocks"],
    "tool definition": ["tools[].function.parameters", "tools[] name, parameters", "tools[] input_schema"],
    "tool call in the reply": ["message.tool_calls, arguments string", "output item function_call, arguments string",
                               "content block tool_use, input object"],
    "tool result sent back": ["role tool with tool_call_id", "item function_call_output with call_id",
                              "user message, tool_result block, tool_use_id"],
    "why it stopped": ["finish_reason", "status and output item types", "stop_reason"],
    "usage": ["prompt_tokens, completion_tokens", "input_tokens, output_tokens", "input_tokens, output_tokens"],
    }
    # END SOLUTION

# %%
REF = json.loads((D.DATA / "reference" / "comparison.json").read_text(encoding="utf-8"))
KEY_TERMS = {  # the one field name each cell must mention
    "system instructions": ["system", "instructions", "system"], "user turn": ["user", "input", "user"],
    "tool definition": ["parameters", "parameters", "input_schema"],
    "tool call in the reply": ["tool_calls", "function_call", "tool_use"],
    "tool result sent back": ["tool_call_id", "call_id", "tool_use_id"],
    "why it stopped": ["finish_reason", "status", "stop_reason"],
    "usage": ["prompt_tokens", "input_tokens", "input_tokens"],
}
try:
    mine = my_table()
except NotImplementedError:
    mine = {a: list(REF[a].values()) for a in ASPECTS}
rows, right = [], 0
for a in ASPECTS:
    for i, s in enumerate(["chat_completions", "responses", "messages"]):
        ok = KEY_TERMS[a][i] in mine[a][i]
        right += ok
        rows.append({"aspect": a, "shape": s, "yours": mine[a][i], "reference": REF[a][s], "match": "✅" if ok else "❌"})
print(pd.DataFrame(rows).to_string(index=False, max_colwidth=46))
llm.check(right == 21, f"{right} of 21 cells name the reference's field")

# %% [markdown]
# 🔍 **Look at** · the last two rows. Code that reads `finish_reason` or `prompt_tokens` breaks when the provider or the
# shape changes. That is the reason for one interface in your code, with the shape handled in one place.

# %% [markdown]
# ## 4 · The same call to a hosted and a local endpoint (7')
#
# `llm.complete` speaks Chat Completions to any OpenAI-compatible server. A local server (Ollama, llama.cpp server,
# vLLM) exposes the same protocol on your machine; here the course starts its own stand-in server on localhost, so
# nothing is downloaded.
#
# ✏️ **Exercise** · Write `ask(provider)` that sends `REQUEST` with `llm.complete(..., provider=provider)` and returns a
# dict: provider, model, the reply's first 60 characters, the finish reason and the usage fields as a dict.

# %%
base = llm.serve_local(8765)
print("local endpoint:", base)
REQUEST = [{"role": "system", "content": "You are Wasil, the rider assistant of Darb Transit Authority. "
                                         'Introduce yourself as: "I am Wasil, Darb\'s AI assistant."'},
           {"role": "user", "content": "Who are you?"}]


def ask(provider: str) -> dict:
    # BEGIN SOLUTION
    r = llm.complete(REQUEST, provider=provider)
    return {"provider": provider, "model": r.model, "reply": llm.text(r)[:60],
            "finish": r.choices[0].finish_reason, "usage": r.usage.model_dump(exclude_none=True)}
    # END SOLUTION


# %%
hosted = llm.PROVIDER if llm.PROVIDER != "local" else "scripted"
try:
    both = [ask(hosted), ask("local")]
except NotImplementedError:
    both = [{"provider": p, "model": llm.complete(REQUEST, provider=p).model} for p in (hosted, "local")]
for b in both:
    print(b)
print("\nWhat changed in code: the provider name, which selects base_url, the key and the model name:")
for p in (hosted, "local"):
    print(f"  {p:10} base_url={llm.PROVIDERS[p]['base_url']} key from {llm.PROVIDERS[p]['key_env']} model={llm.PROVIDERS[p]['model']}")
llm.check(all(b.get("model") for b in both), "one client, two endpoints, the same response shape")

# %% [markdown]
# ## ✱ Stretch · The Responses shape for real
#
# With an OpenRouter key set, send `SHAPES["responses"]["request"]` (with a real model name) through
# `llm.client().responses.create(...)` and compare the reply's items with the recorded one.

# %%
def stretch():
    # BEGIN SOLUTION
    if llm.PROVIDER == "openrouter":
        req = dict(SHAPES["responses"]["request"], model=llm.MODEL)
        r = llm.client().responses.create(**req)
        print([item.type for item in r.output], r.usage)
    else:
        print("skipped: no hosted key in this run")
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Your code reads `choices[0].message.tool_calls`. What breaks when you move to the Messages shape?
# <details><summary>Answer</summary>The call is a content block of type <code>tool_use</code> with its input as an
# object, and the result goes back as a <code>tool_result</code> block in a user message.</details>
#
# 2. What changes in code to move from a hosted model to a local server that speaks Chat Completions?
# <details><summary>Answer</summary>The base URL, the key and the model name: configuration, not code.</details>
#
# 3. Why might a local model still answer differently?
# <details><summary>Answer</summary>A different model, a different chat template and tool-call support: the protocol
# is the same, the behaviour is not. Evaluate it (Day 4) before switching.</details>
#
# **Carry forward.** Every later lab calls models through `llm.complete`, so switching provider is one setting in
# `labs/.env`.
