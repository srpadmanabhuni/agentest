"""Regenerate docs/model-driven/PARITY.md: generic (model-driven) vs v1 per-agent results, cell by cell."""

from __future__ import annotations

import collections
import json
from pathlib import Path

from agentest.model.generic import CHECKS, PORTED_IDS
from agentest.model.runner import parity, run_all, v1_results
from agentest.samples import SAMPLE_AGENT_NAMES

OUT = Path(__file__).resolve().parents[1] / "docs" / "model-driven"
SAMPLES = set(SAMPLE_AGENT_NAMES)

# Why a difference happens. Keyed by (id, kind, agent family); written after reading every row.
WHY = {
    ("T7-004", "generic_stricter", "ref"): "The profile also declares the pii_base/pii_para paraphrase pair; v1 compared only canon vs hinglish. The recorded run really labels the PII paraphrase 'general' instead of 'billing', so this is a genuine extra finding.",
    ("T1-001", "generic_looser", "ref"): "v1 uses a hand-written scenario oracle for case0; the generic profile criterion is a single declarative field test and is weaker. Needs richer per-probe success criteria (see Remaining work).",
    ("T1-003", "generic_looser", "ref"): "v1 requires all three recorded cases (case0..case2, different scenarios) to pass their scenario oracles; the generic profile treats only case0 as canonical (one run), so TSR=1/1. Not a like-for-like comparison.",
    ("T1-018", "generic_looser", "ref"): "v1 flags a write that happened while the scenario oracle failed; the generic check only looks for success words in the final answer vs the declarative criteria, which are weaker for this agent.",
    ("T3-006", "generic_looser", "sample"): "v1 runs the T3-006 scenario and requires the receiving agent's own decision; the generic check only requires that every logged decision is versioned, and the hallucinator's logged decisions are versioned.",
    ("T5-012", "generic_stricter", "sample"): "The generic allowlist is one profile for all scenarios; noop/overreach call user.delete (in the T3-011 scenario), which no correct agent calls. v1's T5-012 scenario only inspects its own run, where they stay within the read allowlist. The generic finding is real but belongs to another scenario.",
}
APPL = {
    ("sample", "n/a"): "Sample-agent profile declares no success criteria / recipients / citations / metamorphic pairs, because sample scenarios judge env postconditions that differ per scenario; v1 runs a scenario-specific oracle.",
    ("sample", "pass"): "v1 marks the ID n/a for this agent family but the generic check finds applicable evidence in the recorded traces (e.g. approvals, authz decisions, write calls) and it passes.",
    ("ref", "n/a"): "The profile does not declare what the check needs (probe role, capability, recipients, citations or approval log) for this agent, so it is n/a; v1 has a hand-written agent-specific check.",
    ("ref", "pass"): "v1 has no surface for the ID on this agent, but the profile declares one (e.g. an approval log or tool list), so the generic check applies and passes.",
    ("ref", "fail"): "v1 has no surface for the ID on this agent, but the profile declares one and the generic check fails.",
}


def fam(a: str) -> str:
    return "sample" if a in SAMPLES else "ref"


def main() -> None:
    gen = run_all()
    par = parity(gen, v1_results())
    t = par["tally"]
    rows = par["rows"]
    per_id = collections.defaultdict(collections.Counter)
    for cells in gen.values():
        for i in cells:
            per_id[i]["cells"] += 1
    for r in rows:
        per_id[r["id"]][r["kind"]] += 1
    total = sum(t.values())
    L = [
        "# Parity: generic (model-driven) checks vs v1 per-agent checks",
        "",
        "Status: **next version (v2.0.0-dev), branch `model-driven` only**. v1.0.0 results are unchanged and remain the reference.",
        "Regenerate with `python scripts/model_parity.py`.",
        "",
        f"Ported IDs: **{len(PORTED_IDS)}** of 130 ({', '.join(PORTED_IDS)}). Agents: **{len(gen)}** (25 reference + 15 sample). Cells compared: **{total}**.",
        "",
        "| bucket | cells | meaning |",
        "|---|---|---|",
        f"| agree (pass/fail identical) | {t['agree']} | same verdict |",
        f"| agree (both n/a) | {t['agree_na']} | both say the agent has no surface |",
        f"| generic stricter | {t['generic_stricter']} | v1 pass, generic fail |",
        f"| generic looser | {t['generic_looser']} | v1 fail, generic pass |",
        f"| applicability differs | {t['applicability']} | one side n/a, the other pass/fail |",
        "",
        f"Where both sides give a pass/fail verdict ({par['comparable']} cells), they agree on **{t['agree']}** "
        f"(**{100 * t['agree'] / max(par['comparable'], 1):.1f}%**). Counting n/a agreement too: {t['agree'] + t['agree_na']}/{total} "
        f"({100 * (t['agree'] + t['agree_na']) / total:.1f}%).",
        "",
        "Honest reading: the generic checks reproduce v1 well where both have evidence, but they are **not yet a replacement**. "
        f"{t['applicability']} cells differ in applicability, mostly because profiles do not yet carry the per-scenario success "
        "criteria and oracles that v1 hard-codes. Some v1 failures (known defects) are n/a in the generic form; those are listed below.",
        "",
        "## Per ID",
        "",
        "| ID | what the generic check verifies | cells | agree+both n/a | stricter | looser | applicability |",
        "|---|---|---|---|---|---|---|",
    ]
    for i in PORTED_IDS:
        c = per_id[i]
        diff = c["generic_stricter"] + c["generic_looser"] + c["applicability"]
        L.append(f"| {i} | {CHECKS[i][0]} | {c['cells']} | {c['cells'] - diff} | {c['generic_stricter']} | {c['generic_looser']} | {c['applicability']} |")
    L += ["", "## Every verdict difference (stricter / looser)", "", "| agent | ID | v1 | generic | generic evidence | why |", "|---|---|---|---|---|---|"]
    for r in rows:
        if r["kind"] in ("generic_stricter", "generic_looser"):
            why = WHY.get((r["id"], r["kind"], fam(r["agent"])), "UNEXPLAINED - investigate")
            L.append(f"| {r['agent']} | {r['id']} | {r['v1']} | {r['generic']} | {r['generic_detail'].replace('|', '/')} | {why} |")
    missed = [r for r in rows if r["kind"] == "applicability" and r["v1"] == "fail"]
    L += ["", f"## Known defects v1 catches that the generic form marks n/a ({len(missed)})", "",
          "These are the main risk of switching: until profiles carry the missing criteria, these defects would go unreported.", "",
          "| agent | ID | v1 evidence |", "|---|---|---|"]
    L += [f"| {r['agent']} | {r['id']} | {r['v1_detail'].replace('|', '/')} |" for r in missed]
    L += ["", "## Every applicability difference", "", "| agent | ID | v1 | generic | why |", "|---|---|---|---|---|"]
    for r in rows:
        if r["kind"] == "applicability":
            side = r["generic"] if r["generic"] != "n/a" else "n/a"
            why = APPL.get((fam(r["agent"]), side), "")
            L.append(f"| {r['agent']} | {r['id']} | {r['v1']} | {r['generic']} | {why} Generic: {r['generic_detail'].replace('|', '/')[:120]} |")
    L.append("")
    (OUT / "PARITY.md").write_text("\n".join(L))
    (OUT / "parity.json").write_text(json.dumps(par, indent=1))
    unexplained = sum("UNEXPLAINED" in x for x in L)
    print(json.dumps(t), f"comparable={par['comparable']}", f"unexplained={unexplained}")


if __name__ == "__main__":
    main()
