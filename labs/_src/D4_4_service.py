# %% [markdown]
# # Lab 4.4 · Wasil as a tested web service
#
# Day 4 · Session 4 (Packaging the assistant as a service) · 25 min.
#
# Darb's app team will call Wasil over HTTP. They need two endpoints, tests that pass without a network or a key, the
# settings in one place, and a cost per 1,000 requests they can put in a budget. This is also the shape of your
# capstone repository.
#
# **Reference state.** `wasil.Wasil` with all its checks, FastAPI and its `TestClient` (installed with the labs), and
# the 40 golden cases from Lab 4.1.
#
# **Tasks**
# - [ ] 1 · The API: health and ask (6')
# - [ ] 2 · Record and replay model responses (7')
# - [ ] 3 · Tests on the recorded responses (6')
# - [ ] 4 · Configuration and cost per 1,000 requests (6')
# - [ ] ✱ Stretch · Run the service and call it from the command line

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

import hashlib
import json
import shutil
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

import llm
import darb as D
import wasil

OUT = Path("artifacts/lab44")
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)
GOLDEN = D.load_jsonl("eval/golden.jsonl")
print(llm.describe())

# %% [markdown]
# ## 1 · The API: health and ask (6')
#
# Two endpoints are enough to start. `GET /health` says the service is up and which provider and model it uses, without
# calling the model. `POST /ask` takes a rider's message and returns Wasil's answer, its kind, citations and flags; the
# request and the response are typed, so a bad request is refused before it costs a call.
#
# ✏️ **Exercise** · Write `make_app(w)` that returns a FastAPI app with both endpoints. `Ask.text` has between 1 and
# 2,000 characters. The response holds no personal data: return Wasil's answer, not the input.

# %%
class Ask(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    received: str | None = Field(default=None, pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class Reply(BaseModel):
    answer: str
    kind: str
    citations: list[str]
    abstained: bool
    flags: list[str]
    disclosure: str


def make_app(w: wasil.Wasil) -> FastAPI:
    app = FastAPI(title="Wasil")
    # BEGIN SOLUTION
    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "provider": llm.PROVIDER, "model": llm.MODEL}

    @app.post("/ask", response_model=Reply)
    def ask(req: Ask) -> Reply:
        out = w.answer(req.text, req.received)
        return Reply(answer=out["answer"], kind=out["kind"], citations=out["citations"], abstained=out["abstained"],
                     flags=out["flags"], disclosure=out["disclosure"])
    # END SOLUTION
    return app


# %%
try:
    client = TestClient(make_app(wasil.Wasil()))
    print(client.get("/health").json())
    r = client.post("/ask", json={"text": "What is the daily fare cap for card payments?", "received": "2026-11-15"})
    print(r.status_code, r.json())
    print(client.post("/ask", json={"text": ""}).status_code, "for an empty message")
except (NotImplementedError, AttributeError) as e:
    print("make_app not written yet")

# %% [markdown]
# ## 2 · Record and replay model responses (7')
#
# Tests that call a hosted model are slow, cost money, fail when the network does, and change when the model does. The
# usual answer is to **record** the model's responses once and **replay** them in tests: the test then checks your
# code (parsing, tools, checks, routing), not the model.
#
# ✏️ **Exercise** · Write `Recorder(path, mode)`, a drop-in for `llm.complete`: in `"record"` mode it calls the real
# function and stores each response under a hash of the request; in `"replay"` mode it returns the stored response and
# raises `KeyError` on a request it has never seen (a test must not reach the model by accident).

# %%
REAL_COMPLETE = llm.complete


class Recorder:
    def __init__(self, path: Path, mode: str = "replay"):
        self.path, self.mode = Path(path), mode
        self.tape = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    @staticmethod
    def key(messages, kw) -> str:
        raw = json.dumps({"messages": messages, **kw}, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:20]

    def __call__(self, messages, **kw):
        # BEGIN SOLUTION
        from openai.types.chat import ChatCompletion
        k = self.key(messages, kw)
        if self.mode == "replay":
            if k not in self.tape:
                raise KeyError(f"no recorded response for request {k}: record again")
            return ChatCompletion.model_validate(self.tape[k])
        resp = REAL_COMPLETE(messages, **kw)
        self.tape[k] = resp.model_dump(mode="json")
        return resp
        # END SOLUTION

    def save(self) -> None:
        self.path.write_text(json.dumps(self.tape, ensure_ascii=False), encoding="utf-8")


# %%
TAPE = OUT / "tape.json"
SUITE = [c for c in GOLDEN if c["category"] in ("tool_use", "grounded")][:12]
try:
    rec = Recorder(TAPE, "record")
    llm.complete = rec
    w = wasil.Wasil()
    RECORDED = [w.answer(c["input"], c["received"])["answer"] for c in SUITE]
    rec.save()
    print(len(rec.tape), "responses recorded for", len(SUITE), "cases")
except NotImplementedError:
    RECORDED = []
    print("Recorder not written yet")
finally:
    llm.complete = REAL_COMPLETE

# %% [markdown]
# 🔍 **Look at** · the tape. Each entry is one model response with its token usage. It is data you can read in a
# review and commit with the tests; re-record it on purpose when you change a prompt or a model.

# %% [markdown]
# ## 3 · Tests on the recorded responses (6')
#
# ✏️ **Exercise** · Write four tests that run on the tape, with no network:
# - `/health` answers 200 without calling the model;
# - `/ask` answers every case in `SUITE` exactly as recorded;
# - an empty message is refused with 422 before any model call;
# - an unrecorded request raises `KeyError` (the tests cannot reach the model).
#
# In your capstone these live in `tests/test_service.py` and run with `pytest`.

# %%
def run_tests() -> dict:
    results = {}
    replay = Recorder(TAPE, "replay")
    llm.complete = replay
    try:
        app = TestClient(make_app(wasil.Wasil()))
        # BEGIN SOLUTION
        results["health without the model"] = app.get("/health").status_code == 200
        got = [app.post("/ask", json={"text": c["input"], "received": c["received"]}).json()["answer"] for c in SUITE]
        results["answers as recorded"] = got == RECORDED
        results["empty message refused"] = app.post("/ask", json={"text": ""}).status_code == 422
        try:
            app.post("/ask", json={"text": "What is the daily fare cap for card payments?"})
            results["unrecorded request stopped"] = False
        except KeyError:
            results["unrecorded request stopped"] = True
        # END SOLUTION
    finally:
        llm.complete = REAL_COMPLETE
    return results


# %%
try:
    T0 = time.perf_counter()
    RESULTS = run_tests()
    for name, ok in RESULTS.items():
        print("✅" if ok else "❌", name)
    print(f"{len(RESULTS)} tests in {time.perf_counter() - T0:.1f} s, no network")
    llm.check(all(RESULTS.values()), "all tests pass on the tape")
except (NotImplementedError, AttributeError):
    print("run_tests not written yet")

# %% [markdown]
# 🔍 **Look at** · a body that is not JSON. A client with a bug sends `{"text": "Was B27 late?"` with no closing brace.
# The typed endpoint refuses it with a 4xx status and a body that says what is wrong, before any model call. A handler
# that parsed the body by hand would raise and answer 500: the client would read a server fault, retry a request that
# can never succeed, and page whoever runs the service.

# %%
try:
    llm.complete = Recorder(TAPE, "replay")  # a model call here would raise KeyError
    bad = TestClient(make_app(wasil.Wasil())).post("/ask", content='{"text": "Was B27 late?"',
                                                    headers={"Content-Type": "application/json"})
    first = bad.json()["detail"][0]
    print(bad.status_code, first["type"], "|", first["msg"])
    llm.check(400 <= bad.status_code < 500 and first["type"] == "json_invalid",
              "a body that is not JSON is the client's error (4xx), named in the reply, and costs no model call")
except (NotImplementedError, AttributeError):
    print("make_app not written yet")
finally:
    llm.complete = REAL_COMPLETE

# %% [markdown]
# ## 4 · Configuration and cost per 1,000 requests (6')
#
# Settings that change between a laptop, a test run and production (provider, model, timeouts, the abstention
# threshold) belong in one place, read from the environment, with defaults that are safe. The cost per 1,000 requests
# comes from **measured** token use on a realistic mix of requests, not from one example.
#
# ✏️ **Exercise** · Write `Settings.from_env()` and `cost_per_1000(prices)`: run the 40 golden cases through Wasil,
# take the mean input and output tokens **per request** (a request may make several model calls) from `llm.LEDGER`, and
# return the cost of 1,000 requests at each example price.

# %%
EXAMPLE_PRICES = {"small open-weight model": (0.10, 0.40), "large frontier model": (3.00, 15.00)}  # per 1M tokens, examples


class Settings(BaseModel):
    provider: str
    model: str
    status_timeout: float = 1.0
    abstain_below: float = 7.0

    @classmethod
    def from_env(cls) -> "Settings":
        # BEGIN SOLUTION
        return cls(provider=os.getenv("LLM_PROVIDER", llm.PROVIDER), model=os.getenv("LLM_MODEL", llm.MODEL),
                   status_timeout=float(os.getenv("WASIL_STATUS_TIMEOUT", "1.0")),
                   abstain_below=float(os.getenv("WASIL_ABSTAIN_BELOW", "7.0")))
        # END SOLUTION


def cost_per_1000(prices: dict) -> dict:
    # BEGIN SOLUTION
    llm.LEDGER.reset()
    w = wasil.Wasil()
    for c in GOLDEN:
        if c["category"] == "extraction":
            wasil.extract(c["input"], c["received"])
        else:
            w.answer(c["input"], c["received"])
    n = len(GOLDEN)
    per_in, per_out = llm.LEDGER.input_tokens / n, llm.LEDGER.output_tokens / n
    print(f"{llm.LEDGER.calls / n:.1f} model calls, {per_in:.0f} input and {per_out:.0f} output tokens per request")
    return {name: round(1000 * (per_in * p[0] + per_out * p[1]) / 1e6, 2) for name, p in prices.items()}
    # END SOLUTION


# %%
try:
    S = Settings.from_env()
    print(S.model_dump())
    COSTS = cost_per_1000(EXAMPLE_PRICES)
    print("cost per 1,000 requests:", COSTS)
    llm.check(COSTS["large frontier model"] > COSTS["small open-weight model"], "the cost is reported per price list")
except NotImplementedError:
    print("Settings or cost_per_1000 not written yet")

# %% [markdown]
# 🔍 **Look at** · calls per request. A complaint that checks the trip status and opens a ticket makes three model
# calls; a question makes one. The mix of requests decides the bill as much as the price does.

# %% [markdown]
# ## ✱ Stretch · Run the service and call it from the command line
#
# Write the app to a file, start it with uvicorn in a separate process, call it with `curl` (or Python's `urllib`), and
# stop it.

# %%
def stretch():
    # BEGIN SOLUTION
    import urllib.request
    (OUT / "service.py").write_text(
        "import os, sys\nsys.path.insert(0, os.environ['LABS_DIR'])\nimport wasil\n"
        "from fastapi import FastAPI\napp = FastAPI()\nw = wasil.Wasil()\n"
        "@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n"
        "@app.post('/ask')\ndef ask(body: dict):\n    out = w.answer(body['text'])\n"
        "    return {'answer': out['answer'], 'citations': out['citations']}\n", encoding="utf-8")
    env = {**os.environ, "LABS_DIR": os.getcwd()}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "service:app", "--app-dir", str(OUT), "--port", "8766"],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                print(urllib.request.urlopen("http://127.0.0.1:8766/health", timeout=1).read().decode())
                break
            except OSError:
                time.sleep(0.5)
        req = urllib.request.Request("http://127.0.0.1:8766/ask", method="POST", headers={"Content-Type": "application/json"},
                                     data=json.dumps({"text": "What is the daily fare cap for card payments?"}).encode())
        print(urllib.request.urlopen(req, timeout=30).read().decode())
        print('the same call with curl: curl -X POST http://127.0.0.1:8766/ask -H "Content-Type: application/json" '
              "-d '{\"text\": \"What is the daily fare cap for card payments?\"}'")
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why test on recorded responses instead of the live model?
# <details><summary>Answer</summary>The test then checks your code, runs in seconds with no key or network, and gives
# the same result every time; the evaluation set is where the live model is measured.</details>
#
# 2. The health check calls the model to prove it works. What goes wrong?
# <details><summary>Answer</summary>Every probe costs a call and counts against the rate limit, and a slow model makes
# the service look down; check the model in a separate, rarer probe.</details>
#
# 3. Why measure cost per request on the golden set, not on one message?
# <details><summary>Answer</summary>Requests differ: complaints make several calls, questions one; only a realistic
# mix gives a number a budget can use.</details>
#
# 4. The app team's client sends `{"text": "Where is my card?", }` (a trailing comma). What should Wasil answer, and
# what should the client do next?
# <details><summary>Answer</summary>A 4xx status (FastAPI answers 422 with type <code>json_invalid</code>; 400 is the
# general status for a malformed request), with a body that names the problem. The client fixes the request and does
# not retry it as it is; a 5xx would wrongly tell it the fault was the server's and that a retry might pass.</details>
#
# **Carry forward.** The capstone repository has this service, these tests in `tests/`, and the cost per 1,000 requests
# in its README.
