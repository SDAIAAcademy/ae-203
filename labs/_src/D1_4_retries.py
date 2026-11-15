# %% [markdown]
# # Lab 1.4 · Timeouts, retries and a fallback model
#
# Day 1 · Session 4 (Streaming, timeouts and retries) · 25 min.
#
# Free hosted models are busy at the worst moments. You measure a streamed reply, then wrap a call in a timeout, a
# retry with backoff and a fallback model, and test each path against a simulated slow endpoint: no model needed, the
# failures happen when the test says so.
#
# **Reference state.** `llm.SlowEndpoint`, a stand-in API that waits or fails according to a plan you give it.
#
# **Tasks**
# - [ ] 1 · Stream a reply and measure the time to first token (6')
# - [ ] 2 · A retry with exponential backoff, only for errors worth retrying (7')
# - [ ] 3 · A fallback model when the primary keeps failing (6')
# - [ ] 4 · Four tests against planned failures (6')
# - [ ] ✱ Stretch · A retry budget shared by all requests

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

import random
import time
import llm
from llm import EndpointError, SlowEndpoint

print(SlowEndpoint([0.1])("Was the Red Line late?", timeout=1.0))

# %% [markdown]
# ## 1 · Stream a reply and measure the time to first token (6')
#
# A streamed reply arrives in pieces. The rider sees the first words after the time to first token (TTFT), long before
# the whole reply is there.
#
# ✏️ **Exercise** · Write `measure_stream(endpoint)` that consumes `endpoint.stream(prompt)` and returns
# `(ttft_seconds, total_seconds, text)`.

# %%
def measure_stream(endpoint: SlowEndpoint) -> tuple[float, float, str]:
    # BEGIN SOLUTION
    t0 = time.perf_counter()
    first, parts = None, []
    for piece in endpoint.stream("Was the Red Line late?"):
        if first is None:
            first = time.perf_counter() - t0
        parts.append(piece)
    return first, time.perf_counter() - t0, "".join(parts).strip()
    # END SOLUTION


# %%
try:
    ttft, total, streamed = measure_stream(SlowEndpoint([]))
except NotImplementedError:
    ttft, total, streamed = 0.6, 1.0, "Route M1 is running 12 minutes late."
print(f"first token after {ttft:.2f} s, whole reply after {total:.2f} s: {streamed!r}")
llm.check(ttft < total, "the rider sees words before the reply is complete")

# %% [markdown]
# ## 2 · A retry with exponential backoff, only for errors worth retrying (7')
#
# Retry a timeout, a 429 (rate limit) and a 5xx (server error). Do **not** retry a 400: the same request will fail the
# same way. Wait `base_delay * 2**attempt` plus a little random jitter between attempts.
#
# ✏️ **Exercise** · Write `call_with_retry(endpoint, prompt, timeout, retries, base_delay)`. It returns the reply, or
# raises the last error after `retries` retries. Record each attempt in the list `log` as `(attempt, outcome)`.

# %%
RETRYABLE = (429, 500, 502, 503, 504)


def call_with_retry(endpoint, prompt: str, timeout: float = 0.5, retries: int = 3, base_delay: float = 0.05,
                    log: list | None = None) -> str:
    log = [] if log is None else log
    # BEGIN SOLUTION
    for attempt in range(retries + 1):
        try:
            reply = endpoint(prompt, timeout=timeout)
            log.append((attempt, "ok"))
            return reply
        except TimeoutError as e:
            log.append((attempt, "timeout"))
            last = e
        except EndpointError as e:
            log.append((attempt, e.status))
            if e.status not in RETRYABLE:
                raise
            last = e
        if attempt < retries:
            time.sleep(base_delay * 2 ** attempt + random.uniform(0, base_delay))
    raise last
    # END SOLUTION


# %%
log = []
try:
    reply = call_with_retry(SlowEndpoint([0.8, 429, 0.1]), "status of M1?", log=log)
except NotImplementedError:
    reply, log = "[primary] Route M1 is running 12 minutes late.", [(0, "timeout"), (1, 429), (2, "ok")]
print(reply, log)
llm.check([o for _, o in log] == ["timeout", 429, "ok"], "a timeout and a 429 were retried, the third attempt answered")

# %% [markdown]
# ## 3 · A fallback model when the primary keeps failing (6')
#
# ✏️ **Exercise** · Write `call_with_fallback(primary, fallback, prompt, ...)`: try the primary with retries; if it still
# fails with a retryable error or a timeout, try the fallback with the same retries. A 400 is raised at once.

# %%
def call_with_fallback(primary, fallback, prompt: str, timeout: float = 0.5, retries: int = 2,
                       log: list | None = None) -> str:
    log = [] if log is None else log
    # BEGIN SOLUTION
    try:
        return call_with_retry(primary, prompt, timeout, retries, log=log)
    except EndpointError as e:
        if e.status not in RETRYABLE:
            raise
    except TimeoutError:
        pass
    log.append(("fallback", fallback.name))
    return call_with_retry(fallback, prompt, timeout, retries, log=log)
    # END SOLUTION


# %%
log = []
try:
    reply = call_with_fallback(SlowEndpoint([0.8, 0.8, 0.8]), SlowEndpoint([0.05], name="fallback"), "M1?", log=log)
except NotImplementedError:
    reply = "[fallback] Route M1 is running 12 minutes late."
print(reply, log)
llm.check(reply.startswith("[fallback]"), "the fallback answered after three timeouts")

# %% [markdown]
# ## 4 · Four tests against planned failures (6')
#
# Three tests are written. ✏️ **Exercise** · Write the fourth, `test_bad_request_is_not_retried`: a 400 must be
# raised after exactly one attempt, and the fallback must not be called.

# %%
def test_slow_then_ok():
    log = []
    assert call_with_retry(SlowEndpoint([0.8, 0.05]), "q", timeout=0.5, log=log).startswith("[primary]")
    assert [o for _, o in log] == ["timeout", "ok"]


def test_rate_limited_twice():
    log = []
    call_with_retry(SlowEndpoint([429, 429, 0.0]), "q", log=log)
    assert len(log) == 3


def test_fallback_after_server_errors():
    assert call_with_fallback(SlowEndpoint([503, 503, 503]), SlowEndpoint([0.0], name="fallback"), "q").startswith("[fallback]")


def test_bad_request_is_not_retried():
    # BEGIN SOLUTION
    primary, fallback, log = SlowEndpoint([400]), SlowEndpoint([0.0], name="fallback"), []
    try:
        call_with_fallback(primary, fallback, "q", log=log)
        raise AssertionError("a 400 must be raised")
    except EndpointError as e:
        assert e.status == 400
    assert primary.calls == 1 and fallback.calls == 0
    # END SOLUTION


# %%
results = {}
for test in (test_slow_then_ok, test_rate_limited_twice, test_fallback_after_server_errors, test_bad_request_is_not_retried):
    try:
        test()
        results[test.__name__] = "pass"
    except NotImplementedError:
        results[test.__name__] = "not written"
    except AssertionError as e:
        results[test.__name__] = f"FAIL {e}"
print(results)
passed = list(results.values()).count("pass")
llm.check(passed == 4, f"{passed} of 4 tests pass")

# %% [markdown]
# 🔍 **Look at** · `llm.complete` does the same for real providers: on a 429 or a 5xx it moves to the next model of
# `LLM_FALLBACKS`. Read it in `labs/llm.py`, and notice what it does not do yet: wait between attempts.

# %% [markdown]
# ## ✱ Stretch · A retry budget
#
# Retries multiply load when a provider is already struggling. Allow at most 10 retries per minute across all calls;
# past that, fail fast to the fallback.

# %%
def stretch():
    # BEGIN SOLUTION
    class Budget:
        def __init__(self, per_minute: int):
            self.per_minute, self.used = per_minute, []

        def take(self) -> bool:
            now = time.monotonic()
            self.used = [t for t in self.used if now - t < 60]
            if len(self.used) >= self.per_minute:
                return False
            self.used.append(now)
            return True

    b = Budget(10)
    print("retries allowed out of 12 asked:", sum(b.take() for _ in range(12)))
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why add random jitter to the backoff?
# <details><summary>Answer</summary>So many clients that failed together do not retry at the same instant and fail
# together again.</details>
#
# 2. A request fails with 400 because the tool schema is invalid. Retry or fallback?
# <details><summary>Answer</summary>Neither: the request is wrong and will fail everywhere. Raise it and fix the
# code.</details>
#
# 3. Streaming cut the time to first token but not the total time. Why does it still matter to the rider?
# <details><summary>Answer</summary>The rider starts reading at once; perceived waiting is the time to the first
# words.</details>
#
# **Carry forward.** The service of Lab 4.4 sets a timeout on every model call and reports failures in its health check.
