"""Run generic checks over all profiled agents and compare with the v1 per-agent results (parity)."""

from __future__ import annotations

import json
from pathlib import Path

from agentest.model.adapters import adapt, record_sample
from agentest.model.generic import CHECKS, PORTED_IDS, evaluate
from agentest.model.profile import Profile, load_all
from agentest.model.trace import Episode
from agentest.paths import episodes_dir, root
from agentest.model.expr import R


def native_episodes(prof: Profile, d: Path | None = None) -> list[dict]:
    """Recorded native episodes for a reference agent, or freshly recorded ones for a sample agent."""
    if prof.adapter == "sample":
        return record_sample(prof.agent, PORTED_IDS_FOR_SAMPLES)
    out: list[dict] = []
    if prof.episodes:
        base = Path(prof.source).parent if prof.source else Path.cwd()
        for f in sorted(base.glob(prof.episodes)):
            out += [json.loads(ln) for ln in f.read_text().splitlines() if ln.strip()]
        return out
    d = d or episodes_dir()
    for f in sorted(d.glob(f"{prof.agent}.jsonl")) + sorted(d.glob(f"{prof.agent}.*.jsonl")):
        out += [json.loads(ln) for ln in f.read_text().splitlines() if ln.strip()]
    return out


def traces(prof: Profile) -> list[Episode]:
    return [adapt(r, prof) for r in native_episodes(prof)]


def run_all(profiles: dict[str, Profile] | None = None) -> dict[str, dict[str, R]]:
    profiles = profiles or load_all()
    return {a: evaluate(p, traces(p)) for a, p in profiles.items()}


def v1_results(path: Path | None = None) -> dict:
    return json.loads((path or root() / "fixtures" / "real" / "v1-results.json").read_text())


def parity(gen: dict[str, dict[str, R]], v1: dict) -> dict:
    """Cell-by-cell comparison over ported IDs. Buckets: agree, generic_stricter, generic_looser, applicability."""
    rows, tally = [], {"agree": 0, "agree_na": 0, "generic_stricter": 0, "generic_looser": 0, "applicability": 0}
    for a, cells in gen.items():
        for tid, r in cells.items():
            old = v1.get(a, {}).get(tid, {"status": "missing", "detail": ""})
            o, n = old["status"], r.status
            if o == n:
                k = "agree_na" if n == "n/a" else "agree"
            elif "n/a" in (o, n) or "missing" in (o, n) or "not-run" in (o, n):
                k = "applicability"
            elif n == "fail":
                k = "generic_stricter"
            else:
                k = "generic_looser"
            tally[k] += 1
            if k not in ("agree", "agree_na"):
                rows.append({"agent": a, "id": tid, "v1": o, "generic": n, "kind": k, "v1_detail": old.get("detail", "")[:160], "generic_detail": r.detail[:160]})
    comparable = tally["agree"] + tally["generic_stricter"] + tally["generic_looser"]
    return {"tally": tally, "comparable": comparable, "rows": rows}


def to_json(gen: dict[str, dict[str, R]]) -> dict:
    return {a: {i: {"status": r.status, "detail": r.detail} for i, r in row.items()} for a, row in gen.items()}


def summary_md(gen: dict[str, dict[str, R]]) -> str:
    sym = {"pass": "P", "fail": "F", "n/a": "-", "not-run": "?"}
    agents = list(gen)
    lines = ["| ID | what | " + " | ".join(agents) + " |", "|---|---|" + "---|" * len(agents)]
    for i in PORTED_IDS:
        lines.append(f"| {i} | {CHECKS[i][0]} | " + " | ".join(sym[gen[a][i].status] for a in agents) + " |")
    return "\n".join(lines)


# Sample agents are recorded on the scenarios whose IDs map to probe roles plus the IDs we port.
PORTED_IDS_FOR_SAMPLES = sorted(set(PORTED_IDS) | {"T1-007", "T1-013", "T3-001", "T4-009", "T2-004", "T2-003", "T5-004", "T5-012", "T3-011"})
