"""Run the 130 universal rules over every agent's OTLP traces and compare with v2.0.0."""

from __future__ import annotations

import json
from pathlib import Path

from agentest.model.adapters import adapt, record_sample
from agentest.model.expr import R
from agentest.model.profile import Profile, get_path
from agentest.paths import episodes_dir, root
from agentest.real.ids import ALL_IDS
from agentest.standards.metadata import Agent, load_all
from agentest.standards.otel import Run, from_otlp, to_otlp


def _profile(a: Agent) -> Profile:
    """Adapter-only view (log -> span mapping). Carries no test logic."""
    ad = a.adapter
    return Profile(agent=a.id, adapter=ad["dialect"], framework=ad.get("framework", ""),
                   tools={n: ("read" if not a.is_write(n) else "write") for n in a.tools},
                   observations=ad.get("observations", {}), episodes=ad.get("episodes", ""), source=str(a.dir / "adapter.json"))


def native(a: Agent) -> list[dict]:
    ad = a.adapter
    if ad["dialect"] == "sample":
        return record_sample(a.id, list(ALL_IDS))
    out: list[dict] = []
    if ad.get("episodes"):
        for f in sorted(a.dir.glob(ad["episodes"])):
            out += [json.loads(ln) for ln in f.read_text().splitlines() if ln.strip()]
        return out
    d = episodes_dir()
    for f in sorted(d.glob(f"{a.id}.jsonl")) + sorted(d.glob(f"{a.id}.*.jsonl")):
        out += [json.loads(ln) for ln in f.read_text().splitlines() if ln.strip()]
    return out


def otlp_docs(a: Agent) -> list[dict]:
    prof = _profile(a)
    obs = a.adapter.get("observations", {})
    docs = []
    for raw in native(a):
        ep = adapt(raw, prof)
        extra = {}
        for k in ("citations", "outputs"):
            vals = [get_path(ep.final_state, p) for p in obs.get(k, [])]
            if obs.get(k):
                extra[f"agentest.{k}"] = [v for v in vals if v]
        docs.append(to_otlp(ep, a.id, extra, *_native_extras(raw, ep, obs)))
    return docs


STEP_KINDS = {"llm", "message", "subagent", "step"}


def _native_extras(raw: dict, ep, obs: dict) -> tuple[list[dict], list[dict], list[str]]:
    """Log fields with an OTel home: tool reasons / source timestamps (span attrs), harness verdicts
    (``gen_ai.evaluation.result``), LLM steps (``chat`` spans). Pure mapping, no verdicts computed here."""
    tr = [t for t in (raw.get("trace") or []) if isinstance(t, dict)]
    tool_attrs: list[dict] = []
    steps: list[str] = []
    for t in tr:
        d = t.get("data")
        if isinstance(d, str):
            try:
                d = json.loads(d)
            except ValueError:
                d = {}
        d = d if isinstance(d, dict) else {}
        if t.get("kind") in ("tool", "write"):
            tool_attrs.append({"agentest.tool.reason": str(d.get("reason") or t.get("reason") or "") or None,
                               "agentest.source.seq": t.get("seq"), "agentest.source.time_s": t.get("mono")})
        elif t.get("kind") in ("llm", "step", "subagent"):
            steps.append(str(d.get("content", ""))[:200] or t.get("kind"))
        elif "reason" in t and "name" in t and "kind" not in t:
            tool_attrs.append({"agentest.tool.reason": str(t.get("reason") or "") or None})
    if len(tool_attrs) != len(ep.tool_calls):
        tool_attrs = tool_attrs[: len(ep.tool_calls)] if tool_attrs else []
    evals = []
    for p in obs.get("evaluation", []):
        v = get_path(raw, p)
        if v is not None:
            evals.append({"gen_ai.evaluation.name": "harness_oracle", "gen_ai.evaluation.score.value": 1.0 if v else 0.0,
                          "gen_ai.evaluation.score.label": "pass" if v else "fail",
                          "gen_ai.evaluation.explanation": str((raw.get("extra") or {}).get("note", ""))[:200] or None})
    mono = [float(t["mono"]) for t in tr if isinstance(t.get("mono"), (int, float))]
    if mono and (ep.duration_s or 0) < max(mono):
        ep.duration_s = max(mono)
    return tool_attrs, evals, steps


def runs(a: Agent) -> list[Run]:
    # Round-trip through OTLP/JSON text: rules only ever see what an OTel collector would see.
    return [from_otlp(json.loads(json.dumps(d))) for d in otlp_docs(a)]


def run_all(agents: dict[str, Agent] | None = None, mode: str = "examples") -> dict[str, dict[str, R]]:
    from agentest.standards.rules import evaluate

    agents = agents or load_all()
    return {k: evaluate(a, runs(a), mode=mode) for k, a in agents.items()}


def to_json(res: dict[str, dict[str, R]]) -> dict:
    return {a: {i: {"status": r.status, "detail": r.detail} for i, r in row.items()} for a, row in res.items()}


def baseline(path: Path | None = None) -> dict:
    return json.loads((path or root() / "fixtures" / "standards" / "v2-baseline.json").read_text())


def regress(v3: dict, v2: dict) -> dict:
    """Defect-catch comparison. A 'defect' is a v2 fail cell."""
    t = {"v2_fail": 0, "caught": 0, "missed_as_pass": 0, "missed_as_na": 0, "v2_pass": 0, "v3_pass_on_v2_pass": 0,
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
                    t["missed_as_pass" if n == "pass" else "missed_as_na"] += 1
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
