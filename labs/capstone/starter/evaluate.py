"""Run an evaluation set through the assistant and log the run.

    uv run python capstone/starter/evaluate.py [--cases path/to/cases.jsonl] [--note "what changed"]

Prints the pass rate per category and every failure, and appends one line to runs.jsonl next to this file:
time, commit, provider, model, cases, pass rate per category and your note. Two such lines, with one stated
change between them, are the "two measured runs" of the capstone README.
"""
import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from service import Settings, build_assistant  # noqa: E402  (also puts the helpers on the path)

import darb as D  # noqa: E402
import llm  # noqa: E402
import wasil  # noqa: E402


def check_case(case: dict, w) -> tuple[bool, str]:
    """The checks of Lab 4.1. Add a branch for every new category your assistant has."""
    e = case["expect"]
    if case["category"] == "extraction":
        obj, _, err = wasil.extract(case["input"], case["received"])
        got = obj.model_dump(mode="json") if obj else None
        if got is None:
            return False, f"no valid object: {err[:60]}"
        wrong = [k for k in e if got.get(k) != e[k]]
        return not wrong, f"wrong {wrong}" if wrong else "ok"
    out = w.answer(case["input"], case["received"])
    if case["category"] == "tool_use":
        called = any(c["name"] == e.get("tool", "get_trip_status") and c["arguments"] == e["args"] for c in out["tool_calls"])
        has = e["answer_contains"] in out["answer"]
        return called and has, "ok" if called and has else f"called={called} contains={has}: {out['answer'][:50]}"
    if case["category"] == "grounded":
        if e["abstain"]:
            return out["abstained"], "ok" if out["abstained"] else f"answered: {out['answer'][:50]}"
        ok = not out["abstained"] and e["cite"] in out["citations"] and e["answer_contains"] in out["answer"]
        return ok, "ok" if ok else f"cites {out['citations']}, abstained={out['abstained']}: {out['answer'][:50]}"
    return False, f"no check for category {case['category']}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(D.DATA / "eval" / "golden.jsonl"))
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    cases = [json.loads(line) for line in Path(args.cases).read_text(encoding="utf-8").splitlines() if line.strip()]
    settings = Settings.from_env()
    w = build_assistant(settings)
    llm.LEDGER.reset()
    by_cat, failures = defaultdict(list), []
    for c in cases:
        ok, detail = check_case(c, w)
        by_cat[c["category"]].append(ok)
        if not ok:
            failures.append((c["id"], c["category"], detail))
    rates = {k: round(sum(v) / len(v), 3) for k, v in sorted(by_cat.items())}
    for k, v in sorted(by_cat.items()):
        print(f"{k:12} {sum(v):3} of {len(v):3}  {sum(v) / len(v):.2f}")
    for f in failures:
        print("FAIL", *f)
    print(llm.LEDGER)

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                                cwd=HERE).stdout.strip()
    except OSError:
        commit = ""
    line = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "commit": commit or "unknown",
            "provider": settings.provider, "model": settings.model, "cases": len(cases), "pass_rate": rates,
            "calls": llm.LEDGER.calls, "input_tokens": llm.LEDGER.input_tokens,
            "output_tokens": llm.LEDGER.output_tokens, "note": args.note}
    with (HERE / "runs.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    print("logged to", HERE / "runs.jsonl")


if __name__ == "__main__":
    main()
