# %% [markdown]
# # Lab 2.4 · Workflow or tool loop
#
# Day 2 · Session 4 (Workflow or agent) · 25 min.
#
# One task, two designs. A rider reports a late or cancelled trip; Wasil must look up the trip status and open a ticket
# that carries the route, the day and what the service says. You write it as a **fixed workflow** (your code decides the
# steps; the model only extracts) and as a **tool loop** (the model decides which tool to call next), run both on ten
# cases, and compare steps, tokens and failures.
#
# **Reference state.** `wasil.extract` (Lab 2.2), `wasil.TOOLS` and `Wasil.call_tool` (Lab 2.3), ten rider messages.
#
# **Tasks**
# - [ ] 1 · The fixed workflow (6')
# - [ ] 2 · The tool loop (7')
# - [ ] 3 · Ten cases through both (6')
# - [ ] 4 · Compare and decide (6')
# - [ ] ✱ Stretch · Add the refund rule as a workflow step

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
import pandas as pd

import llm
import darb as D
import wasil

CASES = [m for m in D.messages() if m["gold"]["complaint_type"] in ("delay", "cancellation")
         and not m["pii"] and not m["injection"]][:10]
print(llm.describe())
for m in CASES:
    print(m["id"], m["lang"], "|", m["text"][:80])


def new_services() -> wasil.Wasil:
    """Fresh services for one run: a trip-status client with a 1 s timeout and an empty ticket list."""
    w = wasil.Wasil.__new__(wasil.Wasil)
    w.provider, w.status, w.tickets, w.STATUS_TIMEOUT = None, D.TripStatus(slow_seconds=1.5), D.Tickets(), 1.0
    return w

# %% [markdown]
# ## 1 · The fixed workflow (6')
#
# ✏️ **Exercise** · Write `workflow(m, svc)`: (1) `wasil.extract(m["text"], m["received"])`; if it returns `None`,
# return `{"ticket": None, "reply": ...}` (human queue); (2) call `get_trip_status` through `svc.call_tool` with the
# extracted route and date; (3) call `create_ticket` with the category, route, date, refund flag and a summary that
# quotes the status (or says the status was unavailable); (4) return the ticket id and a reply written by your code.

# %%
def workflow(m: dict, svc) -> dict:
    # BEGIN SOLUTION
    obj, _, _ = wasil.extract(m["text"], m["received"])
    if obj is None or obj.route is None:
        return {"ticket": None, "reply": "Thank you; a member of staff will read your message."}
    day = (obj.date or D.TODAY).isoformat()
    status = json.loads(svc.call_tool("get_trip_status", json.dumps({"route": obj.route, "date": day})))
    said = (f"status shows {status['delay_minutes']} minutes delay and {status['cancelled_trips']} cancelled trips"
            if "error" not in status else "status unavailable")
    t = json.loads(svc.call_tool("create_ticket", json.dumps({
        "category": obj.complaint_type, "route": obj.route, "date": day, "refund_requested": obj.refund_requested,
        "summary": f"Rider reports {obj.complaint_type} on {obj.route} on {day}; {said}"})))
    return {"ticket": t.get("ticket_id"), "reply": f"I opened ticket {t.get('ticket_id')}; {said}."}
    # END SOLUTION


# %%
svc = new_services()
try:
    out = workflow(CASES[0], svc)
except NotImplementedError:
    out = {"ticket": "DT-1001", "reply": "(reference)"}
print(out, svc.tickets.tickets[-1:] if svc.tickets.tickets else "")

# %% [markdown]
# ## 2 · The tool loop (7')
#
# ✏️ **Exercise** · Write `agent(m, svc, max_steps=4)`: the model gets both tools (`wasil.TOOLS`) and decides. Loop as in
# Lab 2.3, running calls with `svc.call_tool`, until it answers without a tool call or `max_steps` is reached. Return
# the reply and the ticket id, if a ticket was created.

# %%
def agent(m: dict, svc, max_steps: int = 4) -> dict:
    msgs = [{"role": "system", "content": f"You are Wasil, the rider assistant of Darb Transit Authority. Today is "
                                          f"{m['received']}. Look up the trip status, then open a ticket."},
            {"role": "user", "content": m["text"]}]
    ticket = None
    # BEGIN SOLUTION
    for _ in range(max_steps):
        reply = llm.complete(msgs, tools=wasil.TOOLS).choices[0].message
        if not reply.tool_calls:
            return {"ticket": ticket, "reply": reply.content or ""}
        msgs.append(reply.model_dump(exclude_none=True))
        for tc in reply.tool_calls:
            result = svc.call_tool(tc.function.name, tc.function.arguments)
            ticket = json.loads(result).get("ticket_id", ticket)
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    return {"ticket": ticket, "reply": "stopped at the step budget"}
    # END SOLUTION


# %%
svc = new_services()
try:
    out = agent(CASES[0], svc)
except NotImplementedError:
    out = {"ticket": "DT-1001", "reply": "(reference)"}
print(out)

# %% [markdown]
# ## 3 · Ten cases through both (6')
#
# ✏️ **Exercise** · Write `compare(design)`: run `design` on the ten cases with fresh services each, and record per case
# the model calls and tokens it used (difference of `llm.LEDGER` before and after) and whether the ticket is right:
# category, route and date equal to the gold labels.

# %%
def compare(design) -> pd.DataFrame:
    rows = []
    for m in CASES:
        svc = new_services()
        calls0, tok0 = llm.LEDGER.calls, llm.LEDGER.input_tokens + llm.LEDGER.output_tokens
        # BEGIN SOLUTION
        out = design(m, svc)
        t = svc.tickets.tickets[-1] if svc.tickets.tickets else None
        g = m["gold"]
        right = bool(t) and t["category"] == g["complaint_type"] and t["route"] == g["route"] and t["date"] == g["date"]
        rows.append({"id": m["id"], "lang": m["lang"], "model_calls": llm.LEDGER.calls - calls0,
                     "tokens": llm.LEDGER.input_tokens + llm.LEDGER.output_tokens - tok0, "ticket_right": right,
                     "ticket": out["ticket"]})
        # END SOLUTION
    return pd.DataFrame(rows)


# %%
try:
    wf, ag = compare(workflow), compare(agent)
except NotImplementedError:
    wf = pd.DataFrame([{"id": m["id"], "model_calls": 1, "tokens": 600, "ticket_right": True} for m in CASES])
    ag = pd.DataFrame([{"id": m["id"], "model_calls": 3, "tokens": 2600, "ticket_right": True} for m in CASES])
table = pd.DataFrame({
    "workflow": [wf.model_calls.sum(), wf.tokens.sum(), int(wf.ticket_right.sum())],
    "tool loop": [ag.model_calls.sum(), ag.tokens.sum(), int(ag.ticket_right.sum())]},
    index=["model calls", "tokens", "right tickets (of 10)"])
print(table.to_string())

# %% [markdown]
# ## 4 · Compare and decide (6')
#
# ✏️ **Exercise** · Print the cases where the two designs disagree on `ticket_right`, read one of them, and write your
# decision for this task in `DECISION`: which design, and the one number that decided it.

# %%
def decide() -> str:
    # BEGIN SOLUTION
    merged = wf.merge(ag, on="id", suffixes=("_wf", "_loop"))
    print(merged[merged.ticket_right_wf != merged.ticket_right_loop][["id", "ticket_right_wf", "ticket_right_loop"]])
    ratio = ag.tokens.sum() / max(1, wf.tokens.sum())
    return (f"Fixed workflow: the steps never change for this task, and the loop used {ratio:.1f} times the tokens "
            f"for {int(ag.ticket_right.sum())} right tickets against {int(wf.ticket_right.sum())}.")
    # END SOLUTION


try:
    DECISION = decide()
except NotImplementedError:
    DECISION = "(write your decision)"
print(DECISION)
print(llm.LEDGER)
llm.check(table.loc["model calls", "tool loop"] > table.loc["model calls", "workflow"], "the loop pays for its freedom in calls")

# %% [markdown]
# 🔍 **Look at** · a case in which the loop calls a tool the workflow would never call, or skips one. A loop earns its
# cost when the steps depend on what the tools return; here they do not.

# %% [markdown]
# ## ✱ Stretch · The refund rule as a workflow step
#
# Policy P03.1: a metro journey 15 or more minutes late, or a bus journey 25 or more minutes late, earns a refund. Add a
# step that sets `refund_eligible` on the ticket from the status, in code, without asking the model.

# %%
def stretch():
    # BEGIN SOLUTION
    def eligible(route: str, delay: int) -> bool:
        return delay >= (15 if route.startswith("M") else 25)

    for m in CASES:
        g = m["gold"]
        st = D.TripStatus().get(g["route"], g["date"])
        print(m["id"], g["route"], st["delay_minutes"], "min -> refund eligible:", eligible(g["route"], st["delay_minutes"]))
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. When does a tool loop earn its extra calls?
# <details><summary>Answer</summary>When the next step depends on what a tool returned and cannot be written down in
# advance.</details>
#
# 2. In the workflow, who decides that a ticket is opened?
# <details><summary>Answer</summary>Your code; the model only reads the message. That makes the step testable without
# a model.</details>
#
# 3. The refund rule is a fixed threshold. Should the model apply it?
# <details><summary>Answer</summary>No: a rule written in a policy is code. The model can explain it; code applies
# it.</details>
#
# **Carry forward.** Wasil's reference keeps both: a fixed path for complaints and a tool loop where the model must
# choose. Day 3 adds the policy pages.
