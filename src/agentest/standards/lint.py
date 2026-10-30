"""Field linter: which trace / metadata fields are missing and which checks each would unlock.

Evaluates the checks once (verdicts are not changed or reported) and groups every n/a cell by the missing field
named in its detail (guidance.FAMILIES), plus the instrumentation SIGNALS absent from every run."""

from __future__ import annotations

from agentest.standards import guidance, instrumentation, runner


def lint(agent, mode: str = "examples") -> dict:
    res = runner.to_json(runner.run_all({"a": agent}, mode=mode))["a"]
    runs = runner.runs(agent)
    sig = instrumentation.signals(runs)
    fields: dict[str, dict] = {}
    for tid, c in sorted(res.items()):
        if c["status"] != "n/a":
            continue
        g = guidance.guide(tid, c, runs) or {}
        m = (g.get("missing") or "other (see the check's detail)", g.get("how") or f"see docs/tests/{tid}.md")
        f = fields.setdefault(m[0], {"field": m[0], "how": m[1], "unlocks": []})
        f["unlocks"].append(tid)
    na = sum(c["status"] == "n/a" for c in res.values())
    return {"runs": len(runs), "checks": len(res), "n/a": na,
            "absent_signals": [{"signal": k, "field": instrumentation.SIGNALS[k][0]} for k, ok in sig.items() if not ok],
            "missing": sorted(fields.values(), key=lambda f: (-len(f["unlocks"]), f["field"]))}


def text(rep: dict) -> str:
    out = [f"{rep['runs']} run(s); {rep['n/a']} of {rep['checks']} checks n/a"]
    for s in rep["absent_signals"]:
        out.append(f"absent signal: {s['field']}")
    for f in rep["missing"]:
        ids = f["unlocks"]
        out.append(f"missing {f['field']}: unlocks {len(ids)} check(s) ({', '.join(ids[:8])}{', ...' if len(ids) > 8 else ''}); how: {f['how']}")
    return "\n".join(out)
