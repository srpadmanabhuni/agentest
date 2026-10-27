"""Run the 130 universal rules over every agent's OTLP traces and compare with the v2.0.0 verdict baseline."""

from __future__ import annotations

import json
from pathlib import Path

from agentest.paths import root
from agentest.standards.expr import R
from agentest.standards.metadata import Agent, load_all, trace_files
from agentest.standards.otel import Run, from_otlp, read_otlp_file


def otlp_docs(a: Agent) -> list[dict]:
    """Every trace in the agent's OTLP files (one document per traceId)."""
    return [d for f in trace_files(a) for d in read_otlp_file(f)]


def runs(a: Agent) -> list[Run]:
    # Round-trip through OTLP/JSON text: rules only ever see what an OTel collector would see.
    return [from_otlp(json.loads(json.dumps(d))) for d in otlp_docs(a)]


def run_all(agents: dict[str, Agent] | None = None, mode: str = "examples", progress=None) -> dict[str, dict[str, R]]:
    """Evaluate every agent. With a live judge the semantic questions are first collected over all agents and asked
    once each (deduplicated, cached), then the rules run against the answers; questions that only arise from an
    earlier answer are collected in a further round (at most three)."""
    from agentest.standards import judge
    from agentest.standards.rules import evaluate

    agents = agents or load_all()
    loaded = {k: runs(a) for k, a in agents.items()}
    j = judge.active()
    if j is not None and j.url and not j.offline:
        for _ in range(3):
            judge.start_collect()
            for k, a in agents.items():
                evaluate(a, loaded[k], mode=mode)
            if not judge.flush(progress):
                break
    return {k: evaluate(a, loaded[k], mode=mode) for k, a in agents.items()}


def to_json(res: dict[str, dict[str, R]]) -> dict:
    return {a: {i: {"status": r.status, "detail": r.detail, **({"judge": r.judge} if getattr(r, "judge", None) else {})}
                for i, r in row.items()} for a, row in res.items()}


def baseline(path: Path | None = None) -> dict:
    return json.loads((path or root() / "fixtures" / "standards" / "v2-baseline.json").read_text())


def regress(v3: dict, v2: dict) -> dict:
    """Defect-catch comparison. A 'defect' is a v2 fail cell. A cell the judge could not assess (no judge configured)
    is counted apart (missed_as_not_assessed), so a judge-off run can tell 'not caught' from 'not asked'."""
    t = {"v2_fail": 0, "caught": 0, "missed_as_pass": 0, "missed_as_na": 0, "missed_as_not_assessed": 0, "v2_pass": 0, "v3_pass_on_v2_pass": 0,
         "new_fail_on_v2_pass": 0, "new_fail_on_v2_na": 0, "cells": 0}
    missed, new = [], []
    for ag, row in v2.items():
        for tid, old in row.items():
            n = v3.get(ag, {}).get(tid, {"status": "missing"})["status"]
            t["cells"] += 1
            if old["status"] == "fail":
                t["v2_fail"] += 1
                if n == "fail":
                    t["caught"] += 1
                else:
                    t["missed_as_pass" if n == "pass" else "missed_as_not_assessed" if n == "not-assessed" else "missed_as_na"] += 1
                    missed.append({"agent": ag, "id": tid, "v3": n, "v2_detail": old["detail"][:160], "v3_detail": v3.get(ag, {}).get(tid, {}).get("detail", "")[:160]})
            elif old["status"] == "pass":
                t["v2_pass"] += 1
                if n == "pass":
                    t["v3_pass_on_v2_pass"] += 1
                elif n == "fail":
                    t["new_fail_on_v2_pass"] += 1
                    new.append({"agent": ag, "id": tid, "was": "pass", "v3_detail": v3[ag][tid]["detail"][:160]})
            elif n == "fail":
                t["new_fail_on_v2_na"] += 1
                new.append({"agent": ag, "id": tid, "was": old["status"], "v3_detail": v3[ag][tid]["detail"][:160]})
    return {"tally": t, "missed": missed, "new_findings": new}
