"""Responsible Agentic AI Testing Framework v0.1: docs/FRAMEWORK.md and docs/coverage-map.json.

Four pillars (evals, security, privacy, responsible behaviour). Each of the 110 catalogue IDs sits in exactly one
pillar, chosen by its catalogue `eval_group`. Control codes come only from the reviewed vocabulary in
src/agentest/standards/standards_map.yaml (checked against primary sources, see docs/standards/STANDARDS-MAP.md).
The output is test coverage mapping: which tests provide evidence for which control. It is not a compliance
determination and carries no percentage. ``--check`` exits non-zero when a checked-in file is stale (CI).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "checklist-110.jsonl"
ADDITIONS = ROOT / "catalog" / "rai-additions-v1.4.0.jsonl"
ADD_COVERAGE = ROOT / "catalog" / "rai-additions-coverage.json"
SMAP = ROOT / "src" / "agentest" / "standards" / "standards_map.yaml"
OUT_MD = ROOT / "docs" / "FRAMEWORK.md"
OUT_JSON = ROOT / "docs" / "coverage-map.json"
VERSION = "0.1"
DISCLAIMER = "Test coverage, not a compliance determination."

PILLARS = [
    ("evals", "Evals: task success and reliability",
     "Did the agent do the right thing, in the right order, every time? Terminal state, false completion, "
     "dependency order, idempotency, rollback, state across turns and consistency under paraphrase.",
     ("functional", "reliability_robustness", "data_lineage")),
    ("security", "Security",
     "Can untrusted content or a caller make the agent misuse its tools? Prompt injection, tool allowlists, "
     "argument validation, authorisation, approval tokens, delegation and secrets.",
     ("security",)),
    ("privacy", "Privacy",
     "Does personal data stay where it belongs? Identity checks before disclosure, PII in tool arguments, "
     "tenant scoping, revoked consent, soft deletion and masking.",
     ("privacy",)),
    ("responsible", "Responsible behaviour",
     "Does the agent act accountably and fairly? Human approval before irreversible actions, oversight gates, "
     "audit trails, explanations that match actions, and decisions that do not change with language or demographics.",
     ("compliance_governance", "explainability", "bias_fairness")),
]
FAMILIES = [
    ("owasp_llm_2025", "OWASP Top 10 for LLM Applications 2025"),
    ("owasp_agentic_threats_v1", "OWASP Agentic AI Threats and Mitigations v1.0"),
    ("nist_ai_rmf", "NIST AI RMF 1.0 (MEASURE subcategories)"),
    ("nist_ai_600_1", "NIST AI 600-1 GAI risks"),
    ("iso_42001_annex_a", "ISO/IEC 42001:2023 Annex A"),
    ("mitre_atlas", "MITRE ATLAS"),
]


def load():
    cat = [json.loads(line) for line in CATALOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    sm = yaml.safe_load(SMAP.read_text(encoding="utf-8"))
    return cat, sm["vocabulary"], sm["map"]


def build() -> dict:
    cat, vocab, smap = load()
    by_group = {g: p[0] for p in PILLARS for g in p[3]}
    missing = sorted({r["eval_group"] for r in cat} - set(by_group))
    if missing:
        raise SystemExit(f"eval_group without a pillar: {missing}")
    pillars = []
    for key, name, question, groups in PILLARS:
        rows = [r for r in cat if r["eval_group"] in groups]
        controls: dict = {}
        for r in rows:
            for fam, codes in (smap.get(r["id"]) or {}).items():
                for c in codes:
                    if c not in vocab.get(fam, {}):
                        raise SystemExit(f"{r['id']}: {fam} {c} not in the reviewed vocabulary")
                    controls.setdefault(fam, {}).setdefault(c, []).append(r["id"])
        pillars.append({
            "key": key, "name": name, "question": question, "eval_groups": list(groups),
            "tests": [{"id": r["id"], "title": r["title"], "priority": r["priority"], "class": r["class_id"]} for r in rows],
            "test_count": len(rows),
            "p0_count": sum(r["priority"] == "P0" for r in rows),
            "controls": {fam: {c: {"label": vocab[fam][c], "tests": sorted(ids)} for c, ids in sorted(cs.items())}
                         for fam, cs in sorted(controls.items(), key=lambda kv: [f for f, _ in FAMILIES].index(kv[0]))},
        })
    return {
        "name": "Responsible Agentic AI Testing Framework",
        "version": VERSION,
        "disclaimer": DISCLAIMER,
        "catalogue": "Agentic AI Test Checklist 110 (catalog/checklist-110.jsonl)",
        "control_source": "src/agentest/standards/standards_map.yaml (reviewed vocabulary only)",
        "control_families": dict(FAMILIES),
        "test_count": len(cat),
        "pillars": pillars,
        "additions": additions(vocab, by_group),
    }


def additions(vocab: dict, by_group: dict) -> dict:
    """Dataset v1.4.0 responsible-AI additions: placed in a pillar; rules live in rules.py but are not yet counted in the 110 pillar totals."""
    rows = [json.loads(x) for x in ADDITIONS.read_text(encoding="utf-8").splitlines() if x.strip()]
    cov = json.loads(ADD_COVERAGE.read_text(encoding="utf-8"))
    tests = []
    for r in rows:
        for fam, codes in cov[r["id"]].items():
            for c in codes:
                if c not in vocab.get(fam, {}):
                    raise SystemExit(f"{r['id']}: {fam} {c} not in the reviewed vocabulary")
        tests.append({"id": r["id"], "title": r["title"], "priority": r["priority"], "class": r["class_id"],
                      "pillar": by_group[r["eval_group"]], "controls": cov[r["id"]]})
    return {"source": "catalog/rai-additions-v1.4.0.jsonl (dataset v1.4.0 config rai_additions)",
            "status": "rules implemented; not counted in the 110 pillar totals until the catalogue absorbs them", "test_count": len(tests), "tests": tests}


def render_md(d: dict) -> str:
    out = [
        f"# Responsible Agentic AI Testing Framework v{d['version']}", "",
        "> **" + DISCLAIMER + "** This framework says which agentest tests provide evidence for which control. "
        "Passing them does not make a system conformant with any standard or law, and no percentage score is given.", "",
        "The framework groups the 110 tests of the Agentic AI Test Checklist into four pillars. Every test sits in exactly "
        "one pillar, chosen by its catalogue `eval_group`, and every test ID below has a universal rule in agentest "
        "(`agentest std run` returns pass, fail or n/a for it). Control codes are taken only from the reviewed vocabulary in "
        "[`standards_map.yaml`](../src/agentest/standards/standards_map.yaml) (see [Standards map](standards/STANDARDS-MAP.md)).", "",
        "Generated by `python scripts/gen_framework.py` (CI runs `--check`). The same data is machine-readable in "
        "[`coverage-map.json`](coverage-map.json). The 20 repo extensions (`X-001` to `X-020`) are not assigned to a pillar in v0.1.", "",
        "## The four pillars", "",
        "| Pillar | Question it answers | Tests | P0 | Catalogue groups |", "|---|---|---|---|---|",
    ]
    for p in d["pillars"]:
        out.append(f"| [{p['name']}](#{p['key']}) | {p['question']} | {p['test_count']} | {p['p0_count']} | "
                   + ", ".join(f"`{g}`" for g in p["eval_groups"]) + " |")
    es = [p for p in d["pillars"] if p["key"] in ("evals", "security")]
    out += ["", f"Total: {sum(p['test_count'] for p in d['pillars'])} tests.", "",
            "## How to use it", "",
            "1. Pick the pillars that matter for your agent (evals and security together hold "
            f"{sum(p['test_count'] for p in es)} of the {sum(p['test_count'] for p in d['pillars'])} tests and "
            f"{sum(p['p0_count'] for p in es)} of the {sum(p['p0_count'] for p in d['pillars'])} P0 tests).",
            "2. Run the P0 tests of those pillars in CI first; add P1 and P2 as your traces carry the needed signals.",
            "3. Report results per pillar as tests run, passed, failed and n/a, and list the controls those tests map to. "
            "Say \"coverage\" (which tests map to a control), never \"compliance\".", ""]
    for p in d["pillars"]:
        out += [f'<a id="{p["key"]}"></a>', "", f"## {p['name']}", "", p["question"], "",
                "| ID | Class | Priority | Test |", "|---|---|---|---|"]
        out += [f"| {t['id']} | {t['class']} | {t['priority']} | {t['title']} |" for t in p["tests"]]
        out += ["", "**Control coverage** (control: tests that map to it)", ""]
        for fam, cs in p["controls"].items():
            out.append(f"- *{d['control_families'][fam]}*")
            out += [f"  - `{c}` {v['label']}: {', '.join(v['tests'])}" for c, v in cs.items()]
        out.append("")
    a = d["additions"]
    names = {p["key"]: p["name"] for p in d["pillars"]}
    out += ["## Responsible-AI additions (dataset v1.4.0)", "",
            f"{a['test_count']} tests added on 2026-11-04 (config `rai_additions` on the dataset, "
            "[`catalog/rai-additions-v1.4.0.jsonl`](../catalog/rai-additions-v1.4.0.jsonl)). Each has a universal rule in "
            "agentest (`agentest std run --ids …`); they are not counted in the 110 pillar totals above until the "
            "catalogue absorbs them.", "",
            "| ID | Class | Priority | Pillar | Test | Control coverage |", "|---|---|---|---|---|---|"]
    out += [f"| {t['id']} | {t['class']} | {t['priority']} | {names[t['pillar']]} | {t['title']} | "
            + "; ".join(f"{d['control_families'][f]}: {', '.join(cs)}" for f, cs in t["controls"].items()) + " |"
            for t in a["tests"]]
    out.append("")
    out += ["## Versioning", "",
            "v0.1 (November 2026) is a first public draft. Pillar boundaries may change after feedback; changes will be "
            "listed in the [CHANGELOG](../CHANGELOG.md). Suggestions are welcome through GitHub issues.", ""]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if docs/FRAMEWORK.md or docs/coverage-map.json is stale")
    a = ap.parse_args()
    d = build()
    want = {OUT_MD: render_md(d), OUT_JSON: json.dumps(d, indent=2, ensure_ascii=False) + "\n"}
    if a.check:
        stale = [str(p.relative_to(ROOT)) for p, t in want.items() if not p.exists() or p.read_text(encoding="utf-8") != t]
        if stale:
            print("stale, run python scripts/gen_framework.py:", ", ".join(stale))
            return 1
        return 0
    for p, t in want.items():
        p.write_text(t, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
