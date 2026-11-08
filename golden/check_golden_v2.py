"""Re-derive every golden case in golden/golden-cases-v2.jsonl with the agentest checks (offline; judge questions are
answered only from the hand-written labels stored in each case).

Each case is written to a temporary agent directory (agent-card.json, tools.json, traces/), the universal rules run
on it, and the status of the case's own test ID must equal expected_verdict. Exit 1 on any mismatch.
    PYTHONPATH=src python golden/check_golden_v2.py [--file golden/golden-cases-v2.jsonl] [--quiet]"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from agentest.standards import judge, metadata
from agentest.standards.rules import evaluate
from agentest.standards.runner import runs as agent_runs

HERE = Path(__file__).resolve().parent


def materialise(c: dict, root: Path) -> Path:
    d = root / str(c.get("case_id", "case"))
    (d / "traces").mkdir(parents=True, exist_ok=True)
    (d / "agent-card.json").write_text(json.dumps(c["agent_card"], indent=1), encoding="utf-8")
    (d / "tools.json").write_text(json.dumps(c["tools"], indent=1), encoding="utf-8")
    (d / "traces" / "desk.otlp.jsonl").write_text("".join(json.dumps(t) + "\n" for t in c["traces"]), encoding="utf-8")
    return d


LABEL_MODEL = "golden-hand-labels"  # not a model: the judge answers below were written by hand with the case


def use_labels(answers: list[dict], cache: Path) -> None:
    """Replay the case's hand-written answers to the judge questions (offline cache; nothing is sent anywhere).
    No answers = judge off, so a question the case does not answer leaves the check not-assessed."""
    os.environ["AGENTEST_JUDGE_NO_BUNDLED"] = "1"
    judge.configure2("off")
    if not answers:
        judge.configure("off")
        return
    j = judge.Judge(None, LABEL_MODEL, cache=cache, offline=True)
    cache.write_text("".join(json.dumps({"key": j.key_for(x["guide"], x["payload"]), "guide": x["guide"], "model": LABEL_MODEL,
                                         "answer": x["answer"]}, ensure_ascii=False) + "\n" for x in answers), encoding="utf-8")
    judge.configure(None, LABEL_MODEL, None, str(cache), True)


def verdict(c: dict) -> tuple[str, str]:
    """(status, detail) of the case's own test ID, with the case's hand-labelled judge answers (if any)."""
    with tempfile.TemporaryDirectory() as tmp:
        use_labels(c.get("judge_answers") or [], Path(tmp) / "labels.jsonl")
        a = metadata.load(materialise(c, Path(tmp)))
        r = evaluate(a, agent_runs(a), ids=[c["test_id"]], mode="examples")[c["test_id"]]
    return r.status, r.detail


def load(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(HERE / "golden-cases-v2.jsonl"))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    cases = load(Path(a.file))
    bad = 0
    for c in cases:
        got, detail = verdict(c)
        ok = got == c["expected_verdict"]
        bad += not ok
        if not a.quiet or not ok:
            print(f'{"ok " if ok else "BAD"} {c["case_id"]} {c["test_id"]:7} expected={c["expected_verdict"]:5} got={got}'
                  + ("" if ok else f"  ({detail[:160]})"))
    print(f"{len(cases) - bad}/{len(cases)} cases agree; {len({c['test_id'] for c in cases})} test IDs")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
