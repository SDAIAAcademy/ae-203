"""darb.py: the data and services of Darb Transit Authority, and reference versions of what the labs build.

    import darb as D
    msgs = D.messages()                         # 300 rider messages with gold labels
    D.TripStatus().get("M1", "2026-11-14")      # the synthetic trip-status service
    D.Tickets().create(...)                     # the synthetic ticket-creation service
    D.search("How much is a single fare?")      # hybrid search over the 120 policy pages

The reference functions (chunking, search, masking, instruction detection) are what a lab's safety net falls back
on when an exercise is not done yet. Everything here is synthetic.
"""

from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path

LABS = Path(__file__).resolve().parent
DATA = LABS / "data"
TODAY = date(2026, 11, 15)


def load_jsonl(path: str | Path) -> list[dict]:
    p = DATA / path if not Path(path).is_absolute() else Path(path)
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def messages() -> list[dict]:
    return load_jsonl("messages.jsonl")


# ------------------------------------------------------------------ services
class ToolError(Exception):
    """An error a tool returns to the model: it says what was wrong and what to send instead."""


def _net() -> dict:
    return json.loads((DATA / "network.json").read_text(encoding="utf-8"))


class TripStatus:
    """The trip-status service: status of one route on one service day. Route B33's feed answers slowly."""

    def __init__(self, slow_seconds: float = 2.0):
        self.net = _net()
        self.routes = {r["id"]: r for r in self.net["routes"]}
        self.slow_seconds = slow_seconds
        self.calls = 0

    def get(self, route: str, date: str) -> dict:
        self.calls += 1
        if route not in self.routes:
            raise ToolError(f"unknown route {route!r}; send one of {', '.join(self.routes)}")
        first, last = self.net["service_window"]
        if not (first <= date <= last):
            raise ToolError(f"no status for {date}; the service keeps {first} to {last}")
        if route in self.net["slow_routes"]:
            time.sleep(self.slow_seconds)
        return {"route": route, "date": date, **self.net["status"][f"{route}|{date}"]}


CATEGORIES = ["delay", "cancellation", "overcharge", "lost_item", "accessibility", "staff", "cleanliness", "other"]


class Tickets:
    """The ticket-creation service. Keeps tickets in memory; numbers start at DT-1001."""

    def __init__(self):
        self.tickets: list[dict] = []

    def create(self, category: str, route: str | None, date: str | None, summary: str,
               refund_requested: bool = False) -> dict:
        if category not in CATEGORIES:
            raise ToolError(f"unknown category {category!r}; send one of {', '.join(CATEGORIES)}")
        if not summary or len(summary) > 500:
            raise ToolError("summary must be 1 to 500 characters")
        t = {"ticket_id": f"DT-{1001 + len(self.tickets)}", "category": category, "route": route, "date": date,
             "summary": summary, "refund_requested": refund_requested, "state": "open"}
        self.tickets.append(t)
        return {"ticket_id": t["ticket_id"], "state": "open"}


# ------------------------------------------------------------------ the policy corpus
def pages() -> list[dict]:
    """The 120 policy pages: {page, id, lang, title, status, sections: [{ref, heading, text}]}."""
    out = []
    for f in sorted((DATA / "policies").glob("P*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        pid, lang = f.stem.split("_")
        title = lines[0].split("·", 1)[1].strip()
        status = "superseded" if ("superseded" in lines[2] or "ملغاة" in lines[2]) else "in force"
        sections, cur = [], None
        for line in lines[3:]:
            if line.startswith("## "):
                ref, heading = line[3:].split(" ", 1)
                cur = {"ref": ref, "heading": heading, "text": ""}
                sections.append(cur)
            elif cur is not None and line.strip():
                cur["text"] += (" " if cur["text"] else "") + line.strip()
        out.append({"page": f.stem, "id": pid, "lang": lang, "title": title, "status": status,
                    "sections": sections, "text": "\n".join(lines)})
    return out


AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def normalise(text: str) -> str:
    """Lower case; Arabic: no diacritics or tatweel, one form of alef, taa marbuta as haa, alef maqsura as yaa;
    Arabic-Indic digits as Western digits."""
    text = re.sub(r"[ً-ْـ]", "", text.translate(AR_DIGITS))
    text = re.sub("[أإآ]", "ا", text).replace("ة", "ه").replace("ى", "ي")
    return text.lower()


STOP = {"the", "a", "an", "is", "are", "do", "does", "i", "my", "on", "of", "to", "in", "for", "can", "what", "how",
        "and", "or", "be", "it", "at", "with", "if", "will", "me", "هل", "في", "من", "على", "ما", "كم", "الى", "عن",
        "او", "و"}


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"\w+", normalise(text)) if w not in STOP]


def chunk_by_section(pgs: list[dict]) -> list[dict]:
    """One chunk per section, with the page title in front so a chunk stands alone."""
    return [{"chunk": s["ref"] + "_" + p["lang"], "ref": s["ref"], "page": p["page"], "lang": p["lang"],
             "status": p["status"], "text": f"{p['title']}. {s['heading']}. {s['text']}"}
            for p in pgs for s in p["sections"]]


def chunk_fixed(pgs: list[dict], size: int = 300, overlap: int = 50) -> list[dict]:
    """Fixed windows of `size` characters over each page's text, `overlap` characters shared."""
    out = []
    for p in pgs:
        body = p["text"]
        for i, start in enumerate(range(0, max(1, len(body) - overlap), size - overlap)):
            piece = body[start:start + size]
            refs = re.findall(r"## (P\d+\.\d+)", body[:start + size])
            out.append({"chunk": f"{p['page']}#{i}", "ref": refs[-1] if refs else p["id"] + ".1", "page": p["page"],
                        "lang": p["lang"], "status": p["status"], "text": piece})
    return out


# ------------------------------------------------------------------ search
class BM25:
    """Keyword search with BM25 over normalised tokens (rank-bm25)."""

    def __init__(self, chunks: list[dict]):
        from rank_bm25 import BM25Okapi

        self.chunks = chunks
        self.index = BM25Okapi([tokens(c["text"]) or ["_"] for c in chunks])

    def search(self, query: str, k: int = 5) -> list[tuple[float, dict]]:
        scores = self.index.get_scores(tokens(query))
        top = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [(float(scores[i]), self.chunks[i]) for i in top]


class Vectors:
    """Dense vectors computed on the laptop: TF-IDF weights of character 3- to 5-grams, cosine similarity.

    A stand-in for learned embeddings (which come from a model): same interface, no download."""

    def __init__(self, chunks: list[dict], n: tuple[int, int] = (3, 5)):
        import numpy as np

        self.np, self.n, self.chunks = np, n, chunks
        grams = [self._grams(c["text"]) for c in chunks]
        df = Counter(g for gs in grams for g in set(gs))
        self.vocab = {g: i for i, g in enumerate(sorted(df))}
        self.idf = np.array([math.log((1 + len(chunks)) / (1 + df[g])) + 1 for g in sorted(df)])
        self.matrix = np.vstack([self._vec(gs) for gs in grams])

    def _grams(self, text: str) -> list[str]:
        t = " " + " ".join(tokens(text)) + " "
        return [t[i:i + k] for k in range(self.n[0], self.n[1] + 1) for i in range(len(t) - k + 1)]

    def _vec(self, grams: list[str]):
        v = self.np.zeros(len(self.vocab))
        for g, c in Counter(grams).items():
            if g in self.vocab:
                v[self.vocab[g]] = (1 + math.log(c)) * self.idf[self.vocab[g]]
        norm = self.np.linalg.norm(v)
        return v / norm if norm else v

    def search(self, query: str, k: int = 5) -> list[tuple[float, dict]]:
        sims = self.matrix @ self._vec(self._grams(query))
        top = self.np.argsort(-sims)[:k]
        return [(float(sims[i]), self.chunks[i]) for i in top]


def rrf(*rankings: list[tuple[float, dict]], k: int = 60, top: int = 5) -> list[tuple[float, dict]]:
    """Reciprocal rank fusion: each list adds 1 / (k + rank) to a chunk's score."""
    score, keep = Counter(), {}
    for ranking in rankings:
        for rank, (_, c) in enumerate(ranking, 1):
            score[c["chunk"]] += 1 / (k + rank)
            keep[c["chunk"]] = c
    return [(s, keep[cid]) for cid, s in score.most_common(top)]


class Retriever:
    """The reference retriever: section chunks of both languages, BM25 and vectors fused with RRF.

    `search` returns [(score, chunk)]; `best_bm25` is the top BM25 score, used by the abstention rule."""

    def __init__(self, include_superseded: bool = False):
        self.chunks = [c for c in chunk_by_section(pages()) if include_superseded or c["status"] != "superseded"]
        self.bm25, self.vec = BM25(self.chunks), Vectors(self.chunks)

    def search(self, query: str, k: int = 4) -> list[tuple[float, dict]]:
        return rrf(self.bm25.search(query, 20), self.vec.search(query, 20), top=k)

    def best_bm25(self, query: str) -> float:
        return self.bm25.search(query, 1)[0][0]


_retriever = None


def search(query: str, k: int = 4) -> list[tuple[float, dict]]:
    global _retriever
    _retriever = _retriever or Retriever()
    return _retriever.search(query, k)


# ------------------------------------------------------------------ input and output checks (reference)
PII_PATTERNS = {
    "phone": r"(?:\+966|00966|0)5\d{8}\b",
    "national_id": r"(?<![\w-])[12]\d{9}\b",
    "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "card": r"\b(?:\d{4}[ -]?){3}\d{4}\b",
}
NAME_WORDS = r"(?:(?i:my name is|I am|I'm)|اسمي|أنا)\s+((?:[A-Z][\w-]+\s?){1,2}|(?:[؀-ۿ]+\s?){1,2})"


def mask_pii(text: str) -> tuple[str, list[str]]:
    """Replace personal data with typed placeholders; returns (masked text, kinds found)."""
    found = []
    for kind, pat in PII_PATTERNS.items():
        if re.search(pat, text):
            found.append(kind)
            text = re.sub(pat, f"[{kind.upper()}]", text)
    m = re.search(NAME_WORDS, text)
    if m:
        found.append("name")
        rest = text[m.end(1):].lstrip()
        text = text[:m.start(1)] + "[NAME]" + ("" if rest[:1] in ",،." else " ") + rest
    return text, found


INSTRUCTION_PATTERNS = [
    r"ignore (?:all |your )?(?:previous|earlier|prior) (?:instructions|rules)",
    r"disregard (?:the |your )?(?:policy|rules|instructions|policy pages)",
    r"you are now in \w+ mode", r"reveal (?:your )?(?:system prompt|instructions)",
    r"(?:note|new rule) (?:to|for) (?:automated |ai )?assistants",
    r"تجاهل (?:جميع |كل )?(?:التعليمات|القواعد|تعليماتك)", r"للمساعدات الآلية|تنبيه للمساعد",
    r"^assistant,", r"\bSYSTEM:",
]


def instruction_like(text: str) -> bool:
    """True when the text addresses the assistant with instructions (a reference rule set, not a guarantee)."""
    return any(re.search(p, text, re.I | re.M) for p in INSTRUCTION_PATTERNS)
