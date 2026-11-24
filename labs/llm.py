"""llm.py: the course's provider-neutral model client, with a cache, a usage ledger and a token counter.

    import llm
    resp = llm.complete([{"role": "user", "content": "Hello"}])
    print(llm.text(resp), resp.usage)

Providers (set LLM_PROVIDER in labs/.env):
    openrouter  free hosted open-weight models (the default when OPENROUTER_API_KEY is set)
    local       any OpenAI-compatible server: LOCAL_BASE_URL (Ollama, llama.cpp server, vLLM, LM Studio, LiteLLM,
                or the course's own stand-in server started by `serve_local()`)
    scripted    the course's scripted stand-in model: no key, no network. It imitates a model with rules so every
                cell runs offline; its answers are NOT a model's answers. Used when no key is set.

All three return the Chat Completions shape (an `openai` ChatCompletion object), so the code above them does not
change when the provider does.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterator

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:  # python-dotenv is optional
    pass

LABS = Path(__file__).resolve().parent
CACHE = LABS / "cache"  # replayed responses (git-ignored)

PROVIDERS = {
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "key_env": "OPENROUTER_API_KEY",
                   "model": "google/gemma-4-31b-it:free"},
    "local": {"base_url": os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:8765/v1"), "key_env": "LOCAL_API_KEY",
              "model": os.getenv("LOCAL_MODEL", "wasil-stand-in")},
    "scripted": {"base_url": None, "key_env": None, "model": "scripted-stand-in"},
}
PROVIDER = os.getenv("LLM_PROVIDER") or ("openrouter" if os.getenv("OPENROUTER_API_KEY") else "scripted")
MODEL = os.getenv("LLM_MODEL") or PROVIDERS[PROVIDER]["model"]
FALLBACKS = [m for m in os.getenv("LLM_FALLBACKS", "google/gemma-4-26b-a4b-it:free,nvidia/nemotron-3-ultra-550b-a55b:free").split(",") if m]
USE_CACHE = os.getenv("LLM_CACHE", "1") == "1"
QUICK = os.getenv("DARB_QUICK", "0") == "1"


def pick(full, quick):
    """The small value in quick mode (DARB_QUICK=1), the full one otherwise."""
    return quick if QUICK else full


def check(cond: bool, msg: str) -> bool:
    print(("✅ " if cond else "❌ ") + msg)
    return bool(cond)


def describe() -> str:
    note = "  (scripted stand-in: rules, not a model)" if PROVIDER == "scripted" else ""
    return f"provider: {PROVIDER} | model: {MODEL}{note}"


# ------------------------------------------------------------------ the usage ledger
@dataclass
class Ledger:
    calls: int = 0
    cached: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    by_model: dict = field(default_factory=dict)

    def add(self, resp: Any, seconds: float, cached: bool) -> None:
        u = getattr(resp, "usage", None)
        i, o = (u.prompt_tokens, u.completion_tokens) if u else (0, 0)
        self.calls += 1
        self.cached += cached
        self.input_tokens += i
        self.output_tokens += o
        self.seconds += seconds
        m = self.by_model.setdefault(getattr(resp, "model", "?"), [0, 0, 0])
        m[0] += 1
        m[1] += i
        m[2] += o

    def reset(self) -> None:
        self.__init__()

    def cost(self, price_in: float, price_out: float) -> float:
        """Cost in the price's currency, prices per million tokens."""
        return (self.input_tokens * price_in + self.output_tokens * price_out) / 1e6

    def __str__(self) -> str:
        return (f"{self.calls} calls ({self.cached} from cache), {self.input_tokens:,} input and "
                f"{self.output_tokens:,} output tokens, {self.seconds:.1f} s")


LEDGER = Ledger()

# ------------------------------------------------------------------ tokens
_tokenizer = None
TOKENIZER_ID = os.getenv("LLM_TOKENIZER", "Qwen/Qwen3-0.6B")  # an open tokenizer file: a few MB, no model weights


def count_tokens(obj: Any) -> int:
    """Tokens of a string (or a JSON-able object) under an open tokenizer; offline, an estimate of chars / 3.5.

    Every model family has its own tokenizer: use this to compare texts, and the response's usage for billing."""
    global _tokenizer
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, default=str)
    if _tokenizer is None:
        try:
            from tokenizers import Tokenizer

            _tokenizer = Tokenizer.from_pretrained(TOKENIZER_ID)
        except Exception:  # noqa: BLE001 - offline or blocked
            _tokenizer = False
    return len(_tokenizer.encode(text).ids) if _tokenizer else round(len(text) / 3.5)


# ------------------------------------------------------------------ the client
_clients: dict[tuple, Any] = {}


def client(provider: str | None = None, timeout: float = 60, max_retries: int = 0):
    """An OpenAI SDK client pointed at the provider. The same class talks to every OpenAI-compatible server.

    Made once per provider and settings, then reused: its connection pool keeps the TCP and TLS connection open, so
    the second and later calls skip the set-up."""
    from openai import OpenAI

    p = PROVIDERS[provider or PROVIDER]
    if p["base_url"] is None:
        raise ValueError("the scripted provider has no client; call complete()")
    key = os.getenv(p["key_env"] or "", "") or "not-needed"
    k = (p["base_url"], key, timeout, max_retries)
    if k not in _clients:
        _clients[k] = OpenAI(base_url=p["base_url"], api_key=key, timeout=timeout, max_retries=max_retries)
    return _clients[k]


def _cache_key(payload: dict) -> Path:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return CACHE / (hashlib.sha256(raw.encode()).hexdigest()[:24] + ".json")


def complete(messages: list[dict], *, model: str | None = None, provider: str | None = None, tools: list | None = None,
             response_format: dict | None = None, temperature: float = 0, max_tokens: int | None = None,
             timeout: float = 60, use_cache: bool | None = None, **extra):
    """One Chat Completions call through the configured provider. Returns an openai ChatCompletion.

    Identical requests are replayed from labs/cache/ (LLM_CACHE=0 turns that off). On a rate limit or a server error,
    the next model of LLM_FALLBACKS is tried once each."""
    from openai import APIStatusError, RateLimitError
    from openai.types.chat import ChatCompletion

    provider = provider or PROVIDER
    model = model or (MODEL if provider == PROVIDER else PROVIDERS[provider]["model"])
    kw = {k: v for k, v in dict(tools=tools, response_format=response_format, max_tokens=max_tokens, **extra).items()
          if v is not None}
    t0 = time.perf_counter()
    if provider == "scripted":
        resp = ChatCompletion.model_validate(scripted_reply(messages, model=model, **kw))
        LEDGER.add(resp, time.perf_counter() - t0, False)
        return resp
    payload = {"provider": provider, "model": model, "messages": messages, "temperature": temperature, **kw}
    path = _cache_key(payload)
    if (USE_CACHE if use_cache is None else use_cache) and path.exists():
        resp = ChatCompletion.model_validate_json(path.read_text(encoding="utf-8"))
        LEDGER.add(resp, 0.0, True)
        return resp
    c = client(provider, timeout=timeout)
    models = [model] + ([m for m in FALLBACKS if m != model] if provider == "openrouter" else [])
    for i, m in enumerate(models):
        try:
            resp = c.chat.completions.create(model=m, messages=messages, temperature=temperature, **kw)
            break
        except (RateLimitError, APIStatusError) as e:
            status = getattr(e, "status_code", 0)
            if i == len(models) - 1 or not (status == 429 or status >= 500):
                raise
            print(f"   {m} answered {status}; trying {models[i + 1]}")
    LEDGER.add(resp, time.perf_counter() - t0, False)
    CACHE.mkdir(exist_ok=True)
    path.write_text(resp.model_dump_json(), encoding="utf-8")
    return resp


def text(resp: Any) -> str:
    """The text of a Chat Completions response ('' when it only calls tools)."""
    return resp.choices[0].message.content or ""


# ------------------------------------------------------------------ a local OpenAI-compatible server (Lab 1.2)
_servers: dict[int, Any] = {}


def serve_local(port: int = 8765) -> str:
    """Start the course's stand-in model behind an OpenAI-compatible HTTP API on localhost, in a background thread.

    It speaks the same protocol as Ollama, llama.cpp server or vLLM, so `complete(..., provider="local")` reaches it
    exactly as it would reach them. Nothing is downloaded. Returns the base URL."""
    if port in _servers:
        return f"http://127.0.0.1:{port}/v1"
    global Request  # FastAPI resolves the handler's annotations among this module's globals
    import uvicorn
    from fastapi import FastAPI, Request

    app = FastAPI()

    @app.get("/v1/models")
    def models():
        return {"object": "list", "data": [{"id": "wasil-stand-in", "object": "model", "owned_by": "darb-course"}]}

    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        body = await request.json()
        out = scripted_reply(body["messages"], model=body.get("model", "wasil-stand-in"),
                             tools=body.get("tools"), response_format=body.get("response_format"))
        out["usage"].pop("prompt_tokens_details", None)
        out["system_fingerprint"] = "local"
        return out

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    _servers[port] = server
    return f"http://127.0.0.1:{port}/v1"


# ------------------------------------------------------------------ a simulated slow endpoint (Lab 1.4)
class EndpointError(Exception):
    """An error from the simulated endpoint, with an HTTP-like status code."""

    def __init__(self, status: int, message: str):
        super().__init__(f"{status}: {message}")
        self.status = status


class SlowEndpoint:
    """A stand-in for a model API that is slow or failing in a planned way, so retries can be tested without a model.

    plan: one entry per call, in order: a number of seconds to wait before answering, or an int status code to fail
    with (429, 500, 503, 400). Calls past the end of the plan answer at once. `stream()` yields the answer word by
    word with `word_delay` seconds between words."""

    def __init__(self, plan: list, name: str = "primary", answer: str = "Route M1 is running 12 minutes late."):
        self.plan, self.name, self.answer, self.calls = list(plan), name, answer, 0

    def __call__(self, prompt: str, timeout: float) -> str:
        step = self.plan[self.calls] if self.calls < len(self.plan) else 0.0
        self.calls += 1
        if isinstance(step, int) and step >= 400:
            raise EndpointError(step, {429: "rate limited", 400: "bad request"}.get(step, "server error"))
        wait = float(step)
        if wait > timeout:
            time.sleep(timeout)
            raise TimeoutError(f"{self.name} did not answer within {timeout} s")
        time.sleep(wait)
        return f"[{self.name}] {self.answer}"

    def stream(self, prompt: str, first_token_delay: float = 0.6, word_delay: float = 0.05) -> Iterator[str]:
        time.sleep(first_token_delay)
        for w in self.answer.split(" "):
            yield w + " "
            time.sleep(word_delay)


# ================================================================== the scripted stand-in model
# Rules that imitate the behaviour each lab needs, including the mistakes real models make. Not a model.
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
COLOURS = {"red": "M1", "green": "M2", "blue": "M3", "orange": "M4", "الأحمر": "M1", "الأخضر": "M2", "الأزرق": "M3",
           "البرتقالي": "M4", "a7mar": "M1", "a5dar": "M2", "azra2": "M3", "bortoqali": "M4"}
WEEKDAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
            "الاثنين": 0, "الثلاثاء": 1, "الأربعاء": 2, "الخميس": 3, "الجمعة": 4, "السبت": 5, "الأحد": 6}
ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
       "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15}
TYPE_WORDS = [
    ("lost_item", r"left my|nseet|نسيت|lost"),
    ("accessibility", r"lift|mas3ad|مصعد|المصعد|wheelchair|كرسي"),
    ("overcharge", r"charged|5asamo|خُصم|خصموا|double fare|cap"),
    ("cancellation", r"cancel|etlaghat|أُلغيت|ألغيت"),
    ("delay", r"late|ta2a5ar|mit2a5er|تأخر|delay"),
    ("staff", r"driver|sawa2|سائق|السائق|rude"),
    ("cleanliness", r"dirty|wasi5|متسخة|rubbish"),
]


def find_route(t: str) -> tuple[str | None, str | None]:
    """(route id, the raw words) found in a rider's text."""
    m = re.search(r"\b(M[1-4])\b", t)
    if m:
        return m.group(1), m.group(0)
    for word, rid in COLOURS.items():
        if word in t.lower():
            return rid, word
    m = re.search(r"(?:bus|route|bas|el bus|الحافلة|باص)\s*([0-9٠-٩]{2})|the ([0-9]{2}) bus", t, re.I)
    if m:
        num = (m.group(1) or m.group(2))
        return "B" + num.translate(AR_DIGITS), m.group(0)
    return None, None


def find_date(t: str, received: date) -> tuple[str | None, str | None]:
    low = t.lower()
    if re.search(r"\btoday\b|اليوم|elyoum", low):
        return received.isoformat(), "today"
    if re.search(r"yesterday|أمس|\bams\b", low):
        return (received - timedelta(days=1)).isoformat(), "yesterday"
    m = re.search(r"the (\w+) of november", low)
    if m and m.group(1) in ORD:
        return date(2026, 11, ORD[m.group(1)]).isoformat(), m.group(0)
    m = re.search(r"(\d{1,2}) (?:november|نوفمبر)", low)
    if m:
        return date(2026, 11, int(m.group(1))).isoformat(), m.group(0)
    for word, wd in WEEKDAYS.items():
        if re.search(rf"(?:on |يوم ){word}", low):
            back = (received.weekday() - wd) % 7 or 7
            return (received - timedelta(days=back)).isoformat(), word
    return None, None


def find_type(t: str) -> str:
    for name, pat in TYPE_WORDS:
        if re.search(pat, t, re.I):
            return name
    return "other"


def parse_rider_message(t: str, received: date) -> dict:
    """The stand-in's reading of a rider message: route, date, complaint type, refund requested."""
    route, _ = find_route(t)
    d, _ = find_date(t, received)
    return {"route": route, "date": d, "complaint_type": find_type(t),
            "refund_requested": bool(re.search(r"refund|استرداد", t, re.I))}


def _norm(s: str) -> list[str]:
    s = re.sub(r"[ً-ْـ]", "", s.lower().translate(AR_DIGITS))
    s = re.sub("[أإآ]", "ا", s).replace("ة", "ه").replace("ى", "ي")
    stop = {"the", "a", "an", "is", "are", "do", "does", "i", "my", "on", "of", "to", "in", "for", "can", "what",
            "how", "and", "or", "be", "it", "at", "with", "هل", "في", "من", "على", "ما", "كم", "الى", "عن"}
    return [w for w in re.findall(r"\w+", s) if w not in stop and len(w) > 1]


def _completion(model: str, content: str | None = None, tool_calls: list | None = None, prompt: Any = None) -> dict:
    finish = "tool_calls" if tool_calls else "stop"
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = [{"id": f"call_{i + 1}_" + hashlib.md5(json.dumps(tc, sort_keys=True).encode()).hexdigest()[:6], "type": "function",
                              "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False)}}
                             for i, tc in enumerate(tool_calls)]
    pt = count_tokens(prompt)
    ct = count_tokens(content or json.dumps(tool_calls or [], ensure_ascii=False))
    return {"id": "scripted-" + hashlib.md5(json.dumps(prompt, default=str).encode()).hexdigest()[:10],
            "object": "chat.completion", "created": 0, "model": model,
            "choices": [{"index": 0, "finish_reason": finish, "message": msg}],
            "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}}


def _received(messages: list[dict]) -> date:
    for m in messages:
        found = re.search(r"(?:Today is|Received on|received)\D*(\d{4}-\d{2}-\d{2})", str(m.get("content") or ""))
        if found:
            return date.fromisoformat(found.group(1))
    return date(2026, 11, 15)


def scripted_reply(messages: list[dict], model: str = "scripted-stand-in", tools: list | None = None,
                   response_format: dict | None = None, **_) -> dict:
    system = "\n".join(str(m.get("content") or "") for m in messages if m["role"] == "system")
    last = messages[-1]
    users = [m for m in messages if m["role"] == "user"]
    user = str(users[-1]["content"]) if users else ""
    first_user = str(users[0]["content"]) if users else ""
    prompt = {"messages": messages, "tools": tools}
    received = _received(messages)

    # 1. a grader: "PASS" or "FAIL" for an answer against its passage
    if re.search(r"\bgrader\b|faithful", system, re.I):
        passage = re.search(r"PASSAGE:\s*(.*?)\n\s*ANSWER:", user, re.S)
        answer = re.search(r"ANSWER:\s*(.*)$", user, re.S)
        p, a = (passage.group(1) if passage else ""), (answer.group(1) if answer else "")
        nums_ok = set(re.findall(r"\d+", a)) <= set(re.findall(r"\d+", p))
        aw, pw = set(_norm(a)), set(_norm(p))
        covered = len(aw & pw) / max(1, len(aw))
        ok = nums_ok and covered >= 0.75
        reason = "every number and claim appears in the passage" if ok else (
            "a number is not in the passage" if not nums_ok else "part of the answer is not in the passage")
        return _completion(model, json.dumps({"verdict": "PASS" if ok else "FAIL", "reason": reason}), prompt=prompt)

    # 2. tool use: decide a call, or answer from the results
    if tools:
        names = [t.get("function", t).get("name") for t in tools]
        results = [m for m in messages if m["role"] == "tool"]
        calls_made = [tc["function"]["name"] for m in messages if m["role"] == "assistant"
                      for tc in (m.get("tool_calls") or [])]
        msg = parse_rider_message(first_user, received)
        _, raw_route = find_route(first_user)
        if last["role"] == "tool":
            res = str(last.get("content") or "")
            if '"error"' in res:
                err = json.loads(res).get("error", "")
                if "invalid arguments" in err and calls_made.count("get_trip_status") < 2 and msg["route"]:
                    return _completion(model, tool_calls=[{"name": "get_trip_status",
                                                           "arguments": {"route": msg["route"], "date": msg["date"] or received.isoformat()}}], prompt=prompt)
                if "unknown route" in err:
                    return _completion(model, "I could not find that route. Darb runs metro lines M1 to M4 and bus "
                                              "routes B10 to B60; which one did you take?", prompt=prompt)
                return _completion(model, "I could not reach the trip-status service just now. I have noted your "
                                          "message and a staff member will follow up.", prompt=prompt)
            if ("create_ticket" in names and "create_ticket" not in calls_made
                    and msg["complaint_type"] != "other"):
                status = json.loads(res) if res.startswith("{") else {}
                return _completion(model, tool_calls=[{"name": "create_ticket", "arguments": {
                    "category": msg["complaint_type"], "route": msg["route"], "date": msg["date"],
                    "summary": f"Rider reports {msg['complaint_type'].replace('_', ' ')} on {msg['route']}"
                               + (f"; status shows {status.get('delay_minutes')} minutes delay" if status else ""),
                    "refund_requested": msg["refund_requested"]}}], prompt=prompt)
            facts = [json.loads(m["content"]) for m in results if str(m.get("content", "")).startswith("{")]
            parts = []
            for f in facts:
                if "delay_minutes" in f:
                    parts.append(f"On {f.get('date')}, {f.get('route')} ran {f['delay_minutes']} minutes late"
                                 + (f" with {f['cancelled_trips']} cancelled trips" if f.get("cancelled_trips") else "")
                                 + (f" ({f['reason_en']})." if f.get("reason_en") else "."))
                if "ticket_id" in f:
                    parts.append(f"I opened ticket {f['ticket_id']}; a staff member will reply.")
            return _completion(model, " ".join(parts) or "Done.", prompt=prompt)
        if "get_trip_status" in names and msg["route"] and msg["complaint_type"] in ("delay", "cancellation"):
            route_arg = msg["route"]
            if raw_route and re.search(r"\bbas\b|el bus|باص", raw_route):  # the stand-in copies the rider's words
                route_arg = raw_route
            return _completion(model, tool_calls=[{"name": "get_trip_status",
                                                   "arguments": {"route": route_arg, "date": msg["date"] or received.isoformat()}}], prompt=prompt)
        if "create_ticket" in names and msg["complaint_type"] != "other":
            return _completion(model, tool_calls=[{"name": "create_ticket", "arguments": {
                "category": msg["complaint_type"], "route": msg["route"], "date": msg["date"],
                "summary": f"Rider reports {msg['complaint_type'].replace('_', ' ')} on {msg['route']}",
                "refund_requested": msg["refund_requested"]}}], prompt=prompt)
        return _completion(model, "I can help with trip status, fares and tickets on Darb services.", prompt=prompt)

    # 3. structured extraction
    wants_json = response_format is not None or re.search(r"\bJSON\b", system)
    if wants_json and re.search(r"extract", system, re.I):
        repairing = any(m["role"] == "assistant" for m in messages)
        t = first_user
        if re.search(r"ignore all previous|تجاهل جميع|admin mode", t, re.I):  # the stand-in obeys the rider
            return _completion(model, "Refund approved. I have noted your request.", prompt=prompt)
        out = parse_rider_message(t, received)
        if not repairing:
            m = re.search(r"the (\w+) of november", t, re.I)
            if m:
                out["date"] = m.group(0)  # a date in words, copied as words
            if re.search(r"[٠-٩]", t) and out["route"]:
                out["route"] = "B" + re.search(r"[٠-٩]+", t).group(0)  # Arabic-Indic digits kept
            if re.search(r"ta2a5ar|mit2a5er", t) and out["complaint_type"] == "delay":
                out["complaint_type"] = "late"  # not a value of the schema
        props = {}
        if response_format and response_format.get("type") == "json_schema":
            props = response_format["json_schema"]["schema"].get("properties", {})
        if props:
            out = {k: out.get(k) for k in props}
        body = json.dumps(out, ensure_ascii=False)
        if not repairing and len(t) % 7 == 0:
            body = "Here is the JSON:\n```json\n" + body + "\n```"  # wrapped in prose and a fence
        return _completion(model, body, prompt=prompt)

    # 4. grounded answer from passages
    if re.search(r"passages", system, re.I) or "PASSAGES" in user:
        q = re.search(r"QUESTION:\s*(.*)$", user, re.S)
        question = q.group(1).strip() if q else user
        passages = re.findall(r"\[(P\d+\.\d+)\]\s*(.+)", user)
        if re.search(r"ignore all previous|تجاهل جميع|admin mode", question, re.I):  # obeys the rider's instruction
            cite = f" [{passages[0][0]}]" if passages else ""
            return _completion(model, f"Your refund is approved. I have noted your request.{cite}", prompt=prompt)
        if any("automated assistants" in p or "للمساعدات الآلية" in p for _, p in passages):
            return _completion(model, "Your refund is approved. Please send your national ID number and card number "
                                      "here so I can complete it.", prompt=prompt)
        qw = set(_norm(question))
        scored = sorted(((len(qw & set(_norm(p))) / max(1, len(qw)), cid, p) for cid, p in passages), reverse=True)
        if not scored or scored[0][0] < 0.34:
            return _completion(model, "NOT_IN_CORPUS", prompt=prompt)
        best = scored[0]  # on a tie, the passage listed first wins (retrieval order)
        for s in scored:
            if s[0] == best[0] and [c for c, _ in passages].index(s[1]) < [c for c, _ in passages].index(best[1]):
                best = s
        sentences = re.split(r"(?<=[.!؟?])\s+", best[2].strip())
        body = sentences[2:] or sentences  # a chunk starts with its page title and section heading
        sentence = max(body, key=lambda x: (len(qw & set(_norm(x))), len(x)))
        return _completion(model, f"{sentence} [{best[1]}]", prompt=prompt)

    # 5. a plain conversation: follows two lines of the system prompt, when they are there
    intro = re.search(r"Introduce yourself as:\s*\"([^\"]+)\"", system)
    decline = re.search(r"If the request is not about Darb[^:]*:\s*\"([^\"]+)\"", system)
    if re.search(r"who are you|what are you|من أنت", user, re.I):
        return _completion(model, intro.group(1) if intro else "I am a helpful assistant.", prompt=prompt)
    on_topic = re.search(r"bus|metro|line|fare|ticket|refund|card|station|route|trip|حافلة|الحافلة|مترو|أجرة|تذكرة|محطة|درب|darb",
                         user, re.I)
    if not on_topic:
        return _completion(model, decline.group(1) if decline else "Here is a short poem about the sea.", prompt=prompt)
    return _completion(model, "Darb runs four metro lines and eight bus routes. Ask me about a trip, a fare or a "
                              "ticket.", prompt=prompt)
