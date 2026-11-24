# %% [markdown]
# # Lab 2.3 · The trip-status service as a tool
#
# Day 2 · Session 3 (Tool calling) · 25 min.
#
# Riders ask "was my bus late?". Wasil cannot know; Mishal's trip-status service can. You describe the service to the
# model as a typed tool, run the calls it asks for (validating every argument), and handle the three ways a call goes
# wrong: malformed arguments, an error from the service, and a service that does not answer in time.
#
# **AI policy.** Do the first attempt of this lab without AI assistance.
#
# **Reference state.** `darb.TripStatus` (the service; route B33's feed is slow) and `darb.Tickets` (for the stretch).
#
# **Tasks**
# - [ ] 1 · A tool definition from a typed model (5')
# - [ ] 2 · Run a call: validate, execute, return (6')
# - [ ] 3 · Three conversations: correct, malformed, failing (7')
# - [ ] 4 · A test suite for the tool (7')
# - [ ] ✱ Stretch · The ticket service as a second tool

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

import concurrent.futures as cf
import datetime as dt
import json

from pydantic import BaseModel, Field, ValidationError

import llm
import darb as D
import wasil

STATUS = D.TripStatus(slow_seconds=1.5)
TIMEOUT = 0.5  # seconds
print(llm.describe())
print(STATUS.get("M1", "2026-11-14"))


class StatusArgs(BaseModel):
    """Arguments of get_trip_status."""
    route: str = Field(pattern=r"^(M[1-4]|B[0-9]{2})$", description="Route id: M1 to M4, or B and two digits, such as B27")
    date: dt.date = Field(description="The service day, ISO format")

# %% [markdown]
# ## 1 · A tool definition from a typed model (5')
#
# ✏️ **Exercise** · Write `tool_def()` that returns the Chat Completions tool definition of `get_trip_status`: type
# `function`, a name, a description that says what it returns and when to use it, and `StatusArgs`'s JSON Schema as
# `parameters`.

# %%
def tool_def() -> dict:
    # BEGIN SOLUTION
    return {"type": "function", "function": {
        "name": "get_trip_status",
        "description": "Status of one route on one service day: delay in minutes, cancelled trips and the reason. "
                       "Use it whenever a rider asks whether a trip was late or cancelled.",
        "parameters": StatusArgs.model_json_schema()}}
    # END SOLUTION


# %%
try:
    TOOL = tool_def()
except NotImplementedError:
    TOOL = wasil.TOOLS[0]
print(json.dumps(TOOL, indent=1)[:500])
llm.check(TOOL["function"]["parameters"]["required"] == ["route", "date"], "both arguments are required")

# %% [markdown]
# ## 2 · Run a call: validate, execute, return (6')
#
# The model only *asks* for a call. Your code decides whether to run it. Every outcome becomes a JSON string the model
# can read: the result, or `{"error": ...}` that says what to send instead.
#
# ✏️ **Exercise** · Write `run_tool(arguments)`: parse the JSON (error "arguments are not valid JSON"), validate with
# `StatusArgs` (error starting "invalid arguments:" and naming the field), call `STATUS.get` in a thread with
# `TIMEOUT` (error "trip-status did not answer within ..."), and turn a `D.ToolError` into `{"error": str(e)}`.

# %%
def run_tool(arguments: str) -> str:
    # BEGIN SOLUTION
    try:
        raw = json.loads(arguments or "{}")
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"arguments are not valid JSON: {e}"})
    try:
        a = StatusArgs.model_validate(raw)
    except ValidationError as e:
        return json.dumps({"error": "invalid arguments: " + "; ".join(
            f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())})
    ex = cf.ThreadPoolExecutor(1)  # not "with": leaving a with block waits for the slow call to end
    fut = ex.submit(STATUS.get, a.route, a.date.isoformat())
    try:
        return json.dumps(fut.result(timeout=TIMEOUT))
    except cf.TimeoutError:
        return json.dumps({"error": f"trip-status did not answer within {TIMEOUT} s; tell the rider and offer a ticket"})
    except D.ToolError as e:
        return json.dumps({"error": str(e)})
    finally:
        ex.shutdown(wait=False)
    # END SOLUTION


# %%
CASES = ['{"route": "M1", "date": "2026-11-14"}', '{"route": "bas 27", "date": "2026-11-14"}', '{"route": "M1", "date": ',
         '{"route": "B99", "date": "2026-11-14"}', '{"route": "B33", "date": "2026-11-14"}']
try:
    outs = [run_tool(c) for c in CASES]
except NotImplementedError:
    ref = wasil.Wasil.__new__(wasil.Wasil)  # the reference implementation, without building its search index
    ref.status, ref.STATUS_TIMEOUT, ref.tickets = STATUS, TIMEOUT, D.Tickets()
    outs = [ref.call_tool("get_trip_status", c) for c in CASES]
for c, o in zip(CASES, outs):
    print(f"{c:42} -> {o[:110]}")
llm.check("delay_minutes" in outs[0] and all('"error"' in o for o in outs[1:]), "one result and four useful errors")

# %% [markdown]
# 🔍 **Look at** · the caller's deadline. The rider's app waits a fixed time for Wasil's whole answer, and the tool call
# is one step inside it. A step with its own fixed timeout can run on after the app has given up. Pass the time left
# down instead: the call waits `min(TIMEOUT, time left)`, and is not started at all when no time is left.

# %%
import time


def status_by(route: str, date: str, deadline: float) -> dict:
    """get_trip_status within the caller's deadline (a time.monotonic() value)."""
    left = deadline - time.monotonic()
    if left <= 0:
        return {"error": "the caller's deadline has passed; trip-status was not called"}
    wait = min(TIMEOUT, left)
    ex = cf.ThreadPoolExecutor(1)
    fut = ex.submit(STATUS.get, route, date)
    try:
        return fut.result(timeout=wait)
    except cf.TimeoutError:
        return {"error": f"trip-status did not answer within {wait:.2f} s, the time the caller had left"}
    finally:
        ex.shutdown(wait=False)


calls_before, t0 = STATUS.calls, time.monotonic()
late = status_by("B33", "2026-11-14", deadline=t0 + 0.2)
took = time.monotonic() - t0
gone = status_by("M1", "2026-11-14", deadline=t0 - 0.1)
print(late, f"after {took:.2f} s")
print(gone)
llm.check(took < 0.4 and STATUS.calls == calls_before + 1,
          "the call waited only the 0.2 s left, and no call started after the deadline")

# %% [markdown]
# ## 3 · Three conversations: correct, malformed, failing (7')
#
# ✏️ **Exercise** · Write `converse(text, received, max_steps=3)`: the call, execute, return cycle. Send the system
# prompt and the rider's text with `tools=[TOOL]`; while the reply asks for tools, append the assistant message, run each
# call with `run_tool`, append each result as a `tool` message with its `tool_call_id`; return the final text and the list
# of `(name, arguments, result)`.

# %%
SYSTEM = "You are Wasil, the rider assistant of Darb Transit Authority. Today is {received}. Use the tools."


def converse(text: str, received: str = "2026-11-15", max_steps: int = 3) -> tuple[str, list]:
    msgs = [{"role": "system", "content": SYSTEM.format(received=received)}, {"role": "user", "content": text}]
    calls = []
    # BEGIN SOLUTION
    for _ in range(max_steps):
        m = llm.complete(msgs, tools=[TOOL]).choices[0].message
        if not m.tool_calls:
            return m.content or "", calls
        msgs.append(m.model_dump(exclude_none=True))
        for tc in m.tool_calls:
            result = run_tool(tc.function.arguments)
            calls.append((tc.function.name, tc.function.arguments, result))
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    return "I could not finish; a member of staff will follow up.", calls
    # END SOLUTION


# %%
RIDERS = {"correct": "Was the Orange Line late yesterday?", "malformed": "el bas 21 ta2a5ar ams, lesh?",
          "unknown route": "Was bus 99 late yesterday?", "timeout": "Was bus 33 late yesterday?"}
transcripts = {}
for name, text in RIDERS.items():
    try:
        final, calls = converse(text)
    except NotImplementedError:
        final, calls = "(not written yet)", []
    transcripts[name] = calls
    print(f"--- {name}: {text}")
    for c in calls:
        print("   call", c[1], "->", c[2][:100])
    print("   final:", final)
llm.check(len(transcripts["malformed"]) == 2, "the malformed call was repaired on the second call")

# %% [markdown]
# 🔍 **Look at** · the malformed case. The model copied the rider's words ("bas 21") into the argument; the error named
# the pattern, and the second call was right. Without validation, "bas 27" would have reached the service.

# %% [markdown]
# ## 4 · A test suite for the tool (7')
#
# This is the evidence for LO3: tests that include malformed calls, timeouts and tool errors. Two tests are written.
#
# ✏️ **Exercise** · Write the other four: `test_malformed_json`, `test_bad_route_pattern`, `test_unknown_route` and
# `test_timeout`.

# %%
def test_correct_call():
    out = json.loads(run_tool('{"route": "M1", "date": "2026-11-14"}'))
    assert out["route"] == "M1" and "delay_minutes" in out


def test_date_outside_window():
    assert "no status" in json.loads(run_tool('{"route": "M1", "date": "2026-10-01"}'))["error"]


def test_malformed_json():
    # BEGIN SOLUTION
    assert "not valid JSON" in json.loads(run_tool('{"route": "M1", '))["error"]
    # END SOLUTION


def test_bad_route_pattern():
    # BEGIN SOLUTION
    err = json.loads(run_tool('{"route": "B٢٧", "date": "2026-11-14"}'))["error"]
    assert err.startswith("invalid arguments") and "route" in err
    # END SOLUTION


def test_unknown_route():
    # BEGIN SOLUTION
    assert "unknown route" in json.loads(run_tool('{"route": "B99", "date": "2026-11-14"}'))["error"]
    # END SOLUTION


def test_timeout():
    # BEGIN SOLUTION
    err = json.loads(run_tool('{"route": "B33", "date": "2026-11-14"}'))["error"]
    assert "did not answer" in err
    # END SOLUTION

# %%
names = ["test_correct_call", "test_date_outside_window", "test_malformed_json", "test_bad_route_pattern",
         "test_unknown_route", "test_timeout"]
passed = 0
for n in names:
    fn = globals().get(n)
    try:
        if fn is None:
            raise NotImplementedError
        fn()
        passed += 1
        print("pass       ", n)
    except NotImplementedError:
        print("not written", n)
    except AssertionError as e:
        print("FAIL       ", n, e)
llm.check(passed == 6, f"{passed} of 6 tests pass")

# %% [markdown]
# ## ✱ Stretch · The ticket service as a second tool
#
# Add `create_ticket` (from `wasil.TOOLS[1]`) and run "My trip on bus 40 was cancelled yesterday. I want a refund."
# Which tool does the model call first, and what does the ticket's summary say?

# %%
def stretch():
    # BEGIN SOLUTION
    w = wasil.Wasil(slow_seconds=1.5)
    reply, calls = w.tool_loop("My trip on bus 40 was cancelled yesterday. I want a refund.", "2026-11-15")
    for c in calls:
        print(c["name"], c["arguments"], "->", c["result"])
    print(reply)
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. The model asks for `get_trip_status(route="bas 27")`. Who runs the call, and what should come back?
# <details><summary>Answer</summary>Your code runs it, after validation; it returns an error naming the route pattern
# so the model can send <code>B27</code>.</details>
#
# 2. Why return a timeout as a tool result instead of raising it?
# <details><summary>Answer</summary>The model can then tell the rider and offer a ticket; an exception ends the
# conversation with nothing for the rider.</details>
#
# 3. Where would a tool server over the Model Context Protocol change this code?
# <details><summary>Answer</summary>Only in how the tool's definition is discovered and how the call travels; the
# validation and error handling stay the same.</details>
#
# 4. The staff tool gives Wasil 4 s for a ticket. The first model call took 1.1 s and the ticket service 2.5 s. Should
# Wasil start the second model call, which usually takes about 1 s, with its own 10-second timeout?
# <details><summary>Answer</summary>No: 0.4 s are left, so that call would mostly run after the caller has gone. Pass the
# time left down: skip the call (or give it 0.4 s at most) and answer at once that the ticket is open.</details>
#
# **Carry forward.** `wasil.Wasil.call_tool` and `tool_loop` hold this code for both services; Lab 2.4 compares the
# loop with a fixed workflow.
