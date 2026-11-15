"""Wasil as a web service: the capstone starter.

Run from labs/:  uv run uvicorn service:app --app-dir capstone/starter
Settings come from the environment (see Settings); nothing is hard-coded.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent.parent):  # the helpers next to this file, or in labs/
    if (p / "wasil.py").exists():
        sys.path.insert(0, str(p))
        break

from fastapi import FastAPI
from pydantic import BaseModel, Field

import llm
import wasil


class Settings(BaseModel):
    provider: str
    model: str
    status_timeout: float = 1.0
    abstain_below: float = 7.0

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(provider=os.getenv("LLM_PROVIDER", llm.PROVIDER), model=os.getenv("LLM_MODEL", llm.MODEL),
                   status_timeout=float(os.getenv("WASIL_STATUS_TIMEOUT", "1.0")),
                   abstain_below=float(os.getenv("WASIL_ABSTAIN_BELOW", "7.0")))


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


def build_assistant(settings: Settings) -> wasil.Wasil:
    """Replace this with your own assistant, keeping the same answer() contract."""
    w = wasil.Wasil()
    w.STATUS_TIMEOUT = settings.status_timeout
    w.ABSTAIN_BELOW = settings.abstain_below
    return w


def make_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    assistant = build_assistant(settings)
    app = FastAPI(title="Wasil")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "provider": settings.provider, "model": settings.model}

    @app.post("/ask", response_model=Reply)
    def ask(req: Ask) -> Reply:
        out = assistant.answer(req.text, req.received)
        return Reply(answer=out["answer"], kind=out["kind"], citations=out["citations"], abstained=out["abstained"],
                     flags=out["flags"], disclosure=out["disclosure"])

    return app


app = make_app()
