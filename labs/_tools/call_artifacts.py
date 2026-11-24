"""The small artifacts of the slides on calls between services: every number on those slides comes from here.

    uv run python _tools/call_artifacts.py        (from labs/)

Five artifacts, each with a slide example and a parallel example for the notes and the practice questions:
  1. a cut-off reply against a request too large for the context window, from the response metadata (Day 1, S2)
  2. connection set-up per model call, with a new client per call and with one shared client (Day 1, S2)
  3. where a streamed reply gets buffered, from first and last byte at each hop (Day 1, S4)
  4. a caller's deadline passed down the chain, or not (Day 2, S3)
  5. what the service answers to a body that is not valid JSON (Day 4, S4), from a real run of FastAPI

Durations are planned (assumed) values, not measurements, so the output is the same on every computer. Only the
fifth artifact runs code, and its status codes do not depend on the computer either.
"""

import json  # no "from __future__ import annotations": FastAPI must read the handlers' annotations as classes


def show(title: str) -> None:
    print(f"\n=== {title}")


# ------------------------------------------------------------------ 1. cut off or too large
def diagnose(meta: dict, window: int) -> str:
    """Read one response's metadata (Chat Completions names) and say what happened."""
    if meta.get("status") == 400:
        need = meta["input_tokens"] + meta["max_tokens"]
        return (f"request refused: {meta['input_tokens']:,} input + {meta['max_tokens']:,} output allowance = "
                f"{need:,} > {window:,} window; trim the input, retrying the same request fails again")
    if meta["finish_reason"] == "length" and meta["completion_tokens"] >= meta["max_tokens"]:
        return (f"reply cut off: {meta['completion_tokens']} of max_tokens {meta['max_tokens']} used, input "
                f"{meta['prompt_tokens']:,} fits the window; raise max_tokens or ask for less")
    return "complete reply"


WINDOW = 8192  # the context window of the local model in the example, assumed
TRUNC = {
    "slide A (policy summary)": {"status": 200, "finish_reason": "length", "prompt_tokens": 1240,
                                 "completion_tokens": 150, "max_tokens": 150},
    "slide B (long history)": {"status": 400, "input_tokens": 7960, "max_tokens": 400},
    "parallel C (ticket summary)": {"status": 200, "finish_reason": "length", "prompt_tokens": 3105,
                                    "completion_tokens": 256, "max_tokens": 256},
    "parallel D (all passages)": {"status": 400, "input_tokens": 8020, "max_tokens": 256},
    "parallel E (complete)": {"status": 200, "finish_reason": "stop", "prompt_tokens": 2210,
                              "completion_tokens": 88, "max_tokens": 256},
}


# ------------------------------------------------------------------ 2. connection set-up per call
RTT_MS = 40   # assumed round trip to the hosted provider
DNS_MS = 20   # assumed name lookup when nothing is cached
SETUP = {"dns": DNS_MS, "tcp": RTT_MS, "tls": RTT_MS}  # TCP handshake 1 round trip, TLS 1.3 handshake 1 round trip


def setup_log(calls: int, shared: bool) -> list[dict]:
    rows = []
    for i in range(1, calls + 1):
        fresh = (not shared) or i == 1
        rows.append({"call": i, "connection": "new" if fresh else "reused",
                     **({k: v for k, v in SETUP.items()} if fresh else {"dns": 0, "tcp": 0, "tls": 0})})
    return rows


def setup_total(rows: list[dict]) -> int:
    return sum(r["dns"] + r["tcp"] + r["tls"] for r in rows)


# ------------------------------------------------------------------ 3. buffering on the way
def stream_at_hops(first: float, gap: float, chunks: int, hops: list[tuple[str, float, bool]]) -> list[dict]:
    """Chunk times leaving the model server, then at each hop: (name, delay added per chunk, buffers whole reply)."""
    times = [round(first + i * gap, 3) for i in range(chunks)]
    out = [{"hop": "model server sends", "first": times[0], "last": times[-1], "reads": len(times)}]
    for name, delay, buffers in hops:
        times = [round(t + delay, 3) for t in times]
        if buffers:
            times = [times[-1]]  # holds every chunk until the reply is complete, then sends it in one piece
        out.append({"hop": name, "first": times[0], "last": times[-1], "reads": len(times)})
    return out


def first_buffering_hop(rows: list[dict]) -> str | None:
    for prev, row in zip(rows, rows[1:]):
        if row["reads"] == 1 < prev["reads"]:
            return row["hop"]
    return None


# ------------------------------------------------------------------ 4. a caller's deadline
def run_chain(deadline: float, steps: list[tuple[str, float, float]], propagate: bool, reserve: float = 0.0) -> dict:
    """steps: (name, duration, own fixed timeout). Without propagation every step uses its own timeout and the chain
    runs to the end. With propagation a step gets min(own timeout, time left), and a step is not started when less than
    `reserve` seconds are left (the reply is sent at once instead)."""
    t, rows = 0.0, []
    for name, dur, own in steps:
        left = round(deadline - t, 3)
        if propagate and left <= reserve:
            rows.append({"step": name, "start": t, "end": t, "note": f"not started: {left:.1f} s left"})
            break
        limit = min(own, left) if propagate else own
        end = round(t + min(dur, limit), 3)
        note = "timed out" if dur > limit else "done"
        rows.append({"step": name, "start": t, "end": end, "note": note,
                     "after caller left": round(max(0.0, end - max(t, deadline)), 3)})
        t = end
    wasted = round(sum(r.get("after caller left", 0.0) for r in rows), 3)
    return {"rows": rows, "replied at": t, "caller gave up at": deadline, "work after the caller left": wasted}


DEADLINE = 3.0  # the rider app waits 3 s for /ask
CHAIN = [("model call 1: asks for get_trip_status(B33)", 0.9, 10.0),
         ("trip-status B33 (feed answers slowly)", 1.5, 2.0),
         ("model call 2: writes the reply", 1.3, 10.0)]
PARALLEL_DEADLINE = 5.0  # the staff tool waits 5 s for a refund ticket
PARALLEL = [("model call 1: asks for create_ticket", 1.2, 10.0),
            ("ticket service (busy)", 2.6, 4.0),
            ("model call 2: confirms to the rider", 1.6, 10.0)]


# ------------------------------------------------------------------ 5. a body that is not JSON
def malformed_body_run() -> list[dict]:
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    from pydantic import BaseModel, Field

    class Ask(BaseModel):
        text: str = Field(min_length=1, max_length=2000)

    app = FastAPI()

    @app.post("/ask")              # typed: the framework parses and validates before the handler runs
    def ask(req: Ask) -> dict:
        return {"answer": "..."}

    @app.post("/ask-by-hand")      # parses the body by hand: a bad body becomes an unhandled exception
    async def ask_by_hand(request: Request) -> dict:
        body = json.loads(await request.body())
        return {"answer": body["text"]}

    c = TestClient(app, raise_server_exceptions=False)
    bodies = {"missing brace": '{"text": "Was B27 late yesterday?", "received": "2026-11-15"',
              "valid JSON, wrong field": '{"txt": "Was B27 late yesterday?"}'}
    rows = []
    for path in ("/ask", "/ask-by-hand"):
        for name, body in bodies.items():
            r = c.post(path, content=body, headers={"Content-Type": "application/json"})
            detail = r.json()["detail"][0] if r.status_code == 422 else None
            rows.append({"endpoint": path, "body": name, "status": r.status_code,
                         "type": detail and detail["type"], "msg": detail and detail["msg"]})
    return rows


if __name__ == "__main__":
    show("1 · cut off or too large (window %d tokens, assumed)" % WINDOW)
    for name, meta in TRUNC.items():
        print(f"{name:28} {diagnose(meta, WINDOW)}")

    show(f"2 · connection set-up, {RTT_MS} ms round trip and {DNS_MS} ms lookup assumed")
    for label, calls in (("a complaint (slide)", 3), ("a question (parallel)", 1), ("ten complaints in a row (parallel)", 30)):
        new, shared = setup_log(calls, False), setup_log(calls, True)
        print(f"{label:36} new client per call {setup_total(new):5} ms; one shared client {setup_total(shared):4} ms")
    for r in setup_log(3, False):
        print("   new per call:", r)
    for r in setup_log(3, True):
        print("   shared:      ", r)
    calls_a_day = 10_000 * 2  # a mix that averages two model calls per request, as an example
    print(f"{calls_a_day:,} calls a day: {calls_a_day * setup_total(setup_log(1, False)) / 1000 / 60:.0f} minutes of set-up "
          "with a new client per call")

    show("3 · where the stream is buffered (slide)")
    rows = stream_at_hops(0.60, 0.05, 12, [("API gateway forwards", 0.01, False), ("edge proxy, client receives", 0.01, True)])
    for r in rows:
        print(f"   {r['hop']:30} first byte {r['first']:.2f} s  last byte {r['last']:.2f} s  reads {r['reads']}")
    print("   first hop that buffers:", first_buffering_hop(rows))
    show("3 · parallel: the gateway buffers, the proxy does not")
    rows = stream_at_hops(0.45, 0.04, 20, [("API gateway forwards", 0.02, True), ("edge proxy, client receives", 0.01, False)])
    for r in rows:
        print(f"   {r['hop']:30} first byte {r['first']:.2f} s  last byte {r['last']:.2f} s  reads {r['reads']}")
    print("   first hop that buffers:", first_buffering_hop(rows))

    for title, deadline, chain in (("4 · deadline (slide)", DEADLINE, CHAIN), ("4 · deadline (parallel)", PARALLEL_DEADLINE, PARALLEL)):
        for propagate in (False, True):
            show(f"{title}, deadline passed down: {propagate}")
            out = run_chain(deadline, chain, propagate, reserve=1.0)
            for r in out["rows"]:
                print(f"   {r['start']:4.1f} to {r['end']:4.1f} s  {r['step']:46} {r['note']}")
            print(f"   replied at {out['replied at']:.1f} s; caller gave up at {deadline:.1f} s; "
                  f"work after the caller left {out['work after the caller left']:.1f} s")

    show("5 · a body that is not valid JSON (FastAPI, real run)")
    for r in malformed_body_run():
        print("  ", r)
