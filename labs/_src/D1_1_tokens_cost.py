# %% [markdown]
# # Lab 1.1 · Tokens and cost for 10,000 messages
#
# Day 1 · Session 1 (Tokens, context and cost) · 25 min.
#
# Darb Transit Authority expects about 10,000 rider messages a day for Wasil, in Arabic, English, Arabizi and a mix.
# Before choosing a model, count what a message costs in tokens, and turn that into a daily cost and a latency.
# This lab needs no model call: the tokens are counted on your laptop with an open tokenizer.
#
# **Reference state.** The 300 synthetic rider messages in `data/messages.jsonl` and the policy pages. Nothing else.
#
# **Tasks**
# - [ ] 1 · Count tokens per message, by language (5')
# - [ ] 2 · The same policy in Arabic and in English (5')
# - [ ] 3 · What one request really sends (5')
# - [ ] 4 · Daily cost for 10,000 messages at two example prices (5')
# - [ ] 5 · Latency per message and load in the busiest hour (5')
# - [ ] ✱ Stretch · Arabizi against Arabic script for the same complaint

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

import json
import pandas as pd
import llm
import darb as D

MSGS = D.messages()
print(len(MSGS), "messages |", llm.count_tokens("Was the Red Line late yesterday?"), "tokens in a short question")

# %% [markdown]
# ## 1 · Count tokens per message, by language (5')
#
# ✏️ **Exercise** · Write `token_table(msgs)`: one row per language (`en`, `ar`, `arabizi`, `mixed`) with the number of
# messages, the mean characters, the mean tokens (`llm.count_tokens`) and tokens per 100 characters.

# %%
def token_table(msgs: list[dict]) -> pd.DataFrame:
    # BEGIN SOLUTION
    rows = [{"lang": m["lang"], "chars": len(m["text"]), "tokens": llm.count_tokens(m["text"])} for m in msgs]
    df = pd.DataFrame(rows).groupby("lang").agg(messages=("chars", "size"), chars=("chars", "mean"),
                                                tokens=("tokens", "mean"))
    df["tokens_per_100_chars"] = 100 * df.tokens / df.chars
    return df.round(1)
    # END SOLUTION


# %%
try:
    table = token_table(MSGS)
except NotImplementedError:
    rows = [{"lang": m["lang"], "chars": len(m["text"]), "tokens": llm.count_tokens(m["text"])} for m in MSGS]
    table = pd.DataFrame(rows).groupby("lang").mean().round(1)
    table["tokens_per_100_chars"] = (100 * table.tokens / table.chars).round(1)
print(table.to_string())
llm.check(table.loc["ar", "tokens_per_100_chars"] > table.loc["en", "tokens_per_100_chars"],
          "Arabic script costs more tokens per character than English with this tokenizer")

# %% [markdown]
# ## 2 · The same policy in Arabic and in English (5')
#
# Characters are not a fair comparison across scripts. Take the same text in both languages: policy P03 (refunds for
# delays) exists as `P03_en` and `P03_ar`.
#
# ✏️ **Exercise** · Compute `ratio` = tokens of the Arabic page / tokens of the English page, over all 60 policies
# (sum of Arabic tokens / sum of English tokens).

# %%
PAGES = {p["page"]: p["text"] for p in D.pages()}


def corpus_ratio(pages: dict) -> float:
    # BEGIN SOLUTION
    ar = sum(llm.count_tokens(t) for k, t in pages.items() if k.endswith("_ar"))
    en = sum(llm.count_tokens(t) for k, t in pages.items() if k.endswith("_en"))
    return ar / en
    # END SOLUTION


# %%
try:
    ratio = corpus_ratio(PAGES)
except NotImplementedError:
    ratio = sum(llm.count_tokens(t) for k, t in PAGES.items() if k.endswith("_ar")) / sum(
        llm.count_tokens(t) for k, t in PAGES.items() if k.endswith("_en"))
print(f"P03: {llm.count_tokens(PAGES['P03_en'])} tokens in English, {llm.count_tokens(PAGES['P03_ar'])} in Arabic")
print(f"whole corpus: Arabic / English = {ratio:.2f}")
llm.check(ratio > 1, "the same content costs more tokens in Arabic")

# %% [markdown]
# 🔍 **Look at** · The ratio depends on the tokenizer: a model trained with more Arabic text usually has more Arabic
# pieces in its vocabulary. Ask for the usage of a real call (Lab 1.2) before you quote a number for a given model.

# %% [markdown]
# ## 3 · What one request really sends (5')
#
# A request is never just the rider's message. Wasil also sends its instructions and its tool definitions, every time.
#
# ✏️ **Exercise** · Write `request_tokens(message)` that returns a dict with the tokens of `SYSTEM`, of `TOOLS`
# (as JSON), of the message, and their total.

# %%
from wasil import TOOLS

SYSTEM = ("You are Wasil, the rider assistant of Darb Transit Authority. Today is 2026-11-15. Answer only from Darb's "
          "policies and the trip-status service. Never promise a refund: staff decide refunds. Tell riders they are "
          "talking to an AI assistant.")


def request_tokens(message: str) -> dict:
    # BEGIN SOLUTION
    parts = {"system": llm.count_tokens(SYSTEM), "tools": llm.count_tokens(TOOLS), "message": llm.count_tokens(message)}
    parts["total"] = sum(parts.values())
    return parts
    # END SOLUTION


# %%
try:
    sample = request_tokens(MSGS[1]["text"])
except NotImplementedError:
    sample = {"system": llm.count_tokens(SYSTEM), "tools": llm.count_tokens(TOOLS), "message": llm.count_tokens(MSGS[1]["text"])}
    sample["total"] = sum(sample.values())
print(sample)
MEAN_IN = round(llm.count_tokens(SYSTEM) + llm.count_tokens(TOOLS) + pd.Series([llm.count_tokens(m["text"]) for m in MSGS]).mean())
MEAN_OUT = 60  # an assumption: a short reply; measure it on real calls
print("mean input tokens per request:", MEAN_IN, "| assumed output tokens:", MEAN_OUT)
llm.check(sample["tools"] > sample["message"], "the tool definitions weigh more than the rider's message")

# %% [markdown]
# ## 4 · Daily cost for 10,000 messages at two example prices (5')
#
# Providers price input and output tokens separately, per million tokens. The two prices below are **examples to
# compute with, not any provider's price**: take real ones from your provider's pricing page on the day you decide.
# Free hosted models cost nothing but have request limits per minute and per day.
#
# ✏️ **Exercise** · Write `daily_cost(n, tokens_in, tokens_out, price_in, price_out)` in the prices' currency.

# %%
EXAMPLE_PRICES = {"small open-weight model": (0.10, 0.40), "large frontier model": (3.00, 15.00)}  # per 1M tokens


def daily_cost(n: int, tokens_in: float, tokens_out: float, price_in: float, price_out: float) -> float:
    # BEGIN SOLUTION
    return n * (tokens_in * price_in + tokens_out * price_out) / 1_000_000
    # END SOLUTION


# %%
try:
    costs = {name: round(daily_cost(10_000, MEAN_IN, MEAN_OUT, *p), 2) for name, p in EXAMPLE_PRICES.items()}
except NotImplementedError:
    costs = {name: round(10_000 * (MEAN_IN * p[0] + MEAN_OUT * p[1]) / 1e6, 2) for name, p in EXAMPLE_PRICES.items()}
print("per day:", costs)
print("per 1,000 requests:", {k: round(v / 10, 3) for k, v in costs.items()})
llm.check(costs["large frontier model"] > 10 * costs["small open-weight model"], "the price list, not the tokens, decides the order of magnitude")

# %% [markdown]
# ## 5 · Latency per message and load in the busiest hour (5')
#
# A reply's latency is roughly: time to the first token + output tokens / output speed. Use the assumed numbers
# below until you measure them in Lab 1.4. Assume 15% of the day's messages arrive in the busiest hour.
#
# ✏️ **Exercise** · Write `latency(out_tokens, ttft, tokens_per_second)` and compute the requests per second in the
# busiest hour.

# %%
TTFT, TPS, PEAK_SHARE = 0.6, 40, 0.15  # assumptions: seconds to first token, output tokens per second, busiest hour


def latency(out_tokens: int, ttft: float, tokens_per_second: float) -> float:
    # BEGIN SOLUTION
    return ttft + out_tokens / tokens_per_second
    # END SOLUTION


# %%
try:
    per_msg = latency(MEAN_OUT, TTFT, TPS)
except NotImplementedError:
    per_msg = TTFT + MEAN_OUT / TPS
peak_rps = 10_000 * PEAK_SHARE / 3600
print(f"latency per reply: {per_msg:.2f} s | busiest hour: {peak_rps:.2f} requests per second, "
      f"about {peak_rps * per_msg:.1f} in flight at once")
llm.check(per_msg > TTFT, "latency is more than the time to first token")

# %% [markdown]
# ## ✱ Stretch · Arabizi against Arabic script
#
# Write the same complaint in Arabic script and in Arabizi and count both. Which costs more, and which is easier for
# a model to read?

# %%
def stretch():
    # BEGIN SOLUTION
    pair = ("تأخر الباص 27 عشرين دقيقة أمس", "el bas 27 ta2a5ar 3eshreen da2i2a ams")
    print({t: llm.count_tokens(t) for t in pair})
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why compare Arabic and English on the same policy rather than on all messages?
# <details><summary>Answer</summary>The messages differ in content and length; the same policy in two languages
# isolates the cost of the script.</details>
#
# 2. Which part of a request is paid on every call even when the rider writes one word?
# <details><summary>Answer</summary>The instructions and the tool definitions. Lab 2.1 of the next day keeps them
# stable so a provider can cache them.</details>
#
# 3. The busiest hour has 0.42 requests per second. Why does that matter more than the daily total?
# <details><summary>Answer</summary>Rate limits and capacity are per minute; a daily average hides the peak.</details>
#
# **Carry forward.** The token counts and the cost formula return in Lab 4.4, where the service reports its cost per
# 1,000 requests from measured usage.
