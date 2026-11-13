"""wasil.py: the reference assistant of Darb Transit Authority, the supplied starting state of Day 4 and the capstone.

    from wasil import Wasil
    w = Wasil()
    w.answer("Was the Red Line late yesterday?", received="2026-11-15")

It puts together what Days 1 to 3 build: input checks, structured extraction with repair and a human queue, tool
calls to the trip-status and ticket services, grounded answers with citations and abstention, and output checks.
"""

from __future__ import annotations

import json
import re
import concurrent.futures as cf
import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

import darb as D
import llm

Category = Literal["delay", "cancellation", "overcharge", "lost_item", "accessibility", "staff", "cleanliness", "other"]
DISCLOSURE = {"en": "You are talking to Wasil, Darb's AI assistant.", "ar": "أنت تتحدث مع واصل، المساعد الذكي لهيئة درب."}
ABSTAIN = {"en": "I could not find this in Darb's published policies, so I will not guess. You can ask for a member "
                 "of staff in the app or through the contact centre.",
           "ar": "لم أجد هذا في سياسات درب المنشورة، ولن أخمّن. يمكنك طلب التحدث إلى موظف عبر التطبيق أو مركز الاتصال."}


class RiderMessage(BaseModel):
    """What the assistant needs from a rider's message."""
    route: str | None = Field(default=None, pattern=r"^(M[1-4]|B[0-9]{2})$", description="Route id: M1 to M4, or B and two digits")
    date: dt.date | None = Field(default=None, description="The service day the message is about, ISO format")
    complaint_type: Category
    refund_requested: bool


class StatusArgs(BaseModel):
    route: str = Field(pattern=r"^(M[1-4]|B[0-9]{2})$", description="Route id: M1 to M4, or B and two digits, such as B27")
    date: dt.date


class TicketArgs(BaseModel):
    category: Category
    route: str | None = Field(default=None, pattern=r"^(M[1-4]|B[0-9]{2})$")
    date: dt.date | None = None
    summary: str = Field(min_length=1, max_length=500)
    refund_requested: bool = False


def tool_def(name: str, description: str, model: type[BaseModel]) -> dict:
    return {"type": "function", "function": {"name": name, "description": description,
                                             "parameters": model.model_json_schema()}}


TOOLS = [
    tool_def("get_trip_status", "Status of one route on one service day: delay in minutes, cancelled trips, reason.",
             StatusArgs),
    tool_def("create_ticket", "Open a ticket for a rider's complaint or request. Returns the ticket id.", TicketArgs),
]

EXTRACT_SYSTEM = ("Extract the rider message as one JSON object matching this JSON Schema, and nothing else. "
                  "Received on {received}; resolve words like 'yesterday' from that date.\n{schema}")


def extract(text: str, received: str, repairs: int = 2, provider: str | None = None) -> tuple[RiderMessage | None, int, str]:
    """(object or None, attempts, last error). None means: send it to the human queue."""
    schema = RiderMessage.model_json_schema()
    fmt = {"type": "json_schema", "json_schema": {"name": "RiderMessage", "schema": schema}}
    msgs = [{"role": "system", "content": EXTRACT_SYSTEM.format(received=received, schema=json.dumps(schema))},
            {"role": "user", "content": text}]
    err = ""
    for attempt in range(repairs + 1):
        reply = llm.text(llm.complete(msgs, response_format=fmt, provider=provider))
        s, e = reply.find("{"), reply.rfind("}")
        try:
            return RiderMessage.model_validate_json(reply[s:e + 1] if s >= 0 else reply), attempt, ""
        except ValidationError as ex:
            err = str(ex).splitlines()[0] + " " + "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in ex.errors())
            msgs += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": f"That JSON is invalid: {err}. Reply with the corrected JSON only."}]
    return None, repairs + 1, err


def lang_of(text: str) -> str:
    return "ar" if len(re.findall(r"[؀-ۿ]", text)) > len(re.findall(r"[A-Za-z]", text)) else "en"


class Wasil:
    STATUS_TIMEOUT = 1.0  # seconds before a trip-status call counts as failed
    ABSTAIN_BELOW = 7.0   # the best BM25 score under which the corpus is taken to hold no answer

    def __init__(self, provider: str | None = None, slow_seconds: float = 2.0):
        self.provider = provider
        self.retriever = D.Retriever()
        self.status = D.TripStatus(slow_seconds=slow_seconds)
        self.tickets = D.Tickets()
        self.human_queue: list[dict] = []
        self.log: list[dict] = []

    # ---------------------------------------------------------------- tools
    def call_tool(self, name: str, arguments: str) -> str:
        try:
            raw = json.loads(arguments or "{}")
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"arguments are not valid JSON: {e}"})
        try:
            if name == "get_trip_status":
                a = StatusArgs.model_validate(raw)
                with cf.ThreadPoolExecutor(1) as ex:
                    fut = ex.submit(self.status.get, a.route, a.date.isoformat())
                    try:
                        return json.dumps(fut.result(timeout=self.STATUS_TIMEOUT))
                    except cf.TimeoutError:
                        return json.dumps({"error": f"trip-status for {a.route} did not answer within "
                                                    f"{self.STATUS_TIMEOUT} s; tell the rider and open a ticket"})
            if name == "create_ticket":
                a = TicketArgs.model_validate(raw)
                return json.dumps(self.tickets.create(a.category, a.route, a.date and a.date.isoformat(),
                                                      a.summary, a.refund_requested))
            return json.dumps({"error": f"unknown tool {name!r}"})
        except ValidationError as e:
            return json.dumps({"error": "invalid arguments: " + "; ".join(
                f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())})
        except D.ToolError as e:
            return json.dumps({"error": str(e)})

    def tool_loop(self, text: str, received: str, max_steps: int = 4) -> tuple[str, list[dict]]:
        msgs = [{"role": "system", "content": f"You are Wasil, the rider assistant of Darb Transit Authority. Today is "
                                              f"{received}. Use the tools; never promise a refund."},
                {"role": "user", "content": text}]
        calls = []
        for _ in range(max_steps):
            m = llm.complete(msgs, tools=TOOLS, provider=self.provider).choices[0].message
            if not m.tool_calls:
                return m.content or "", calls
            msgs.append(m.model_dump(exclude_none=True))
            for tc in m.tool_calls:
                result = self.call_tool(tc.function.name, tc.function.arguments)
                calls.append({"name": tc.function.name, "arguments": json.loads(tc.function.arguments or "{}"),
                              "result": json.loads(result)})
                msgs.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        return "I could not finish this request; a member of staff will follow up.", calls

    # ---------------------------------------------------------------- grounded answers
    def grounded(self, question: str) -> dict:
        lang = lang_of(question)
        hits = self.retriever.search(question, 4)
        flagged = [c["ref"] for _, c in hits if D.instruction_like(c["text"])]
        hits = [(s, c) for s, c in hits if c["ref"] not in flagged]
        if not hits or self.retriever.best_bm25(question) < self.ABSTAIN_BELOW:
            return {"answer": ABSTAIN[lang], "citations": [], "abstained": True, "flagged_passages": flagged}
        passages = "\n".join(f"[{c['ref']}] {c['text']}" for _, c in hits)
        system = ("Answer the rider's question only from the passages. Cite the passage id in square brackets, "
                  "like [P03.1]. If the passages do not hold the answer, reply exactly NOT_IN_CORPUS.")
        reply = llm.text(llm.complete([{"role": "system", "content": system},
                                       {"role": "user", "content": f"PASSAGES:\n{passages}\n\nQUESTION: {question}"}],
                                      provider=self.provider)).strip()
        cites = re.findall(r"\[(P\d+\.\d+)\]", reply)
        known = {c["ref"] for _, c in hits}
        if "NOT_IN_CORPUS" in reply or not cites or not set(cites) <= known:
            return {"answer": ABSTAIN[lang], "citations": [], "abstained": True, "flagged_passages": flagged}
        return {"answer": reply, "citations": cites, "abstained": False, "flagged_passages": flagged}

    # ---------------------------------------------------------------- one rider message
    def answer(self, text: str, received: str | None = None) -> dict:
        received = received or D.TODAY.isoformat()
        masked, pii = D.mask_pii(text)
        flags = ["instruction_in_message"] if D.instruction_like(masked) else []
        route, _ = llm.find_route(masked)
        kind = "complaint" if route in self.status.routes and llm.find_type(masked) != "other" else "question"
        out = {"kind": kind, "disclosure": DISCLOSURE[lang_of(text)], "pii_masked": pii, "flags": flags,
               "tool_calls": [], "citations": [], "abstained": False, "extracted": None}
        if kind == "question":
            g = self.grounded(masked)
            out.update(answer=g["answer"], citations=g["citations"], abstained=g["abstained"])
            if g["flagged_passages"]:
                out["flags"].append("instruction_in_passage")
        else:
            obj, attempts, err = extract(masked, received, provider=self.provider)
            out["extracted"] = obj.model_dump(mode="json") if obj else None
            if obj is None:
                self.human_queue.append({"text": masked, "error": err})
                out["answer"] = "Thank you. A member of staff will read your message and reply."
            else:
                reply, calls = self.tool_loop(masked, received)
                out.update(answer=reply, tool_calls=calls)
        # output checks: no personal data, no promise the assistant may not make
        out["answer"], leaked = D.mask_pii(out["answer"])
        if leaked or re.search(r"refund (?:is |has been )?approved|national ID number", out["answer"], re.I):
            out["flags"].append("output_blocked")
            out["answer"] = ABSTAIN[lang_of(text)]
        self.log.append({"input": masked, "kind": kind, "flags": out["flags"]})
        return out
