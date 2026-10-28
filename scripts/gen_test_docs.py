#!/usr/bin/env python3
"""Generate docs/tests/<ID>.md for all checks from the vendored catalogue,
the v3 universal rules, the standards map and the scenario oracles.

Usage: PYTHONPATH=src python scripts/gen_test_docs.py
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from agentest.refs import BIB, refs_for
from agentest.standards import DATA, judge
from agentest.standards.catalog import ALL_IDS, X_IDS, catalogue, what
from agentest.standards.rules import RULES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "tests"
SMAP = yaml.safe_load((DATA / "standards_map.yaml").read_text())
SCEN = yaml.safe_load((DATA / "scenarios.yaml").read_text())
GUIDES = judge.guides()


def judged(i: str) -> list[str]:
    """Scoring guides the rule's published description names (``judge: <guide>``); doc text only, never a verdict."""
    txt = RULES[i][0]
    return sorted(g for g in GUIDES if "judge" in txt and re.search(r"(?<![\w-])" + re.escape(g) + r"(?![\w-])", txt))
MT = {"T7-001", "T7-002", "T7-003"}


def _block(expr: str) -> list[str]:
    return ["```python", expr.strip(), "```", ""]


def render(i: str, cat: dict, res: dict) -> str:
    """Markdown for one test ID."""
    row = cat.get(i, {})
    kind = "Repo extension (not in the 110-row catalogue)" if i in X_IDS else f"Catalogue ID · class {row.get('class_id')} {row.get('class_name', '')}"
    L = [f"# {i} — {row.get('title') or what(i)}", "", f"*{kind}*  ", f"Severity: {row.get('severity', 'n/a')} · Priority: {row.get('priority', 'n/a')} · Oracle: {row.get('oracle_type', 'deterministic')}", ""]
    L += ["## Purpose", "", row.get("objective") or what(i), "", "## What the runner checks", "", what(i), ""]
    if row.get("acceptance_criteria"):
        L += ["Catalogue acceptance criteria:", "", "> " + row["acceptance_criteria"], ""]
    L += ["## Preconditions", "", "- `pip install -e \".[dev]\"`; no network, no API key, no model needed to judge recorded traces.",
          "- Each agent is a folder of standard files only: `agent-card.json` (A2A), `tools.json` (MCP tools/list) and `traces/*.otlp.jsonl` (OTel GenAI). "
          "See the [User Guide](../USER-GUIDE.md).", ""]
    L += ["## How it is judged (v3, standards-based)", "",
          f"**Universal rule** (`src/agentest/standards/rules.py`, the same for every agent): {RULES[i][0]}", "",
          "Inputs: OTel GenAI spans (OTLP/JSON) + the agent's A2A AgentCard, MCP tool annotations and, where needed, "
          "the governance extension `urn:agentest:a2a-ext:governance:v1`. No agent-specific expectation exists.", ""]
    gs = judged(i)
    if gs:
        L += ["**Semantic part (LLM judge).** Structural trace checks run first; the meaning question is answered by the "
              "pluggable judge (any OpenAI-compatible endpoint; default a local Qwen2.5-7B via llama.cpp; temperature 0, "
              "fixed seed, JSON answer, cached) with the versioned scoring guide(s) "
              + ", ".join(f"[`{g}` v{GUIDES[g].get('version', 1)}](../../src/agentest/standards/guides/{g}.yaml)" for g in gs)
              + ". The judge model and guide versions are recorded in each result. Without a judge the verdict is "
              "`not-assessed`; there is no regex or keyword fallback.", ""]
    exp = (SCEN.get("expect") or {}).get(i)
    if exp:
        L += ["**Conformance-scenario oracle** (test-owned, `scenarios.yaml`; applies only to the sample-agent fixture runs whose input id is this ID; "
              "every other trace is judged by the universal rule above):", ""]
        L += _block(exp)
    sm = SMAP["map"].get(i, {})
    if sm:
        L += ["## Standards mapping", ""] + [f"- **{fam}**: " + ", ".join(f"{x} ({SMAP['vocabulary'][fam][x]})" for x in ids) for fam, ids in sm.items()] + [""]
    L += ["## How to run", "", "```bash", f"agentest std run --ids {i}                       # every bundled agent",
          f"agentest std run --ids {i} --agents path/to/agents   # your own agent folders",
          f"agentest std run --ids {i} --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json", "```", ""]
    L += ["## How to interpret", "", "- `pass`: the rule held on every recorded trace of that agent.", "- `fail`: at least one episode violated it; the `detail` field names the evidence (tool call, output excerpt, row).",
          "- `n/a`: the agent's traces and metadata carry no signal for this check (the detail says which one is missing).",
          "- `not-assessed`: the verdict needs a semantic judgement and no judge answer was available (no judge configured, "
          "or an offline replay without a cached answer). It is neither a pass nor a fail.", ""]
    if res:
        cnt = {s: sum(1 for v in res.values() if v == s) for s in ("pass", "fail", "n/a", "not-assessed")}
        L += [f"Current matrix: {cnt['pass']} pass · {cnt['fail']} fail · {cnt['n/a']} n/a across {len(res)} agents.", "",
              "| agent | status |", "|:--|:--|"] + [f"| {a} | {s} |" for a, s in res.items()] + [""]
    L += ["## Known limits", "", "- Small k (1–3 runs per probe); a pass is evidence, not proof.",
          "- Sample-agent results (the 15 non-`aNN` agents) come from scripted behaviours; they validate the rule, not a real model."]
    if judged(i):
        L.append("- The bundled judge is an uncalibrated local 7B model with open scoring guides; its answers can be wrong. "
                 "Results record the judge identity and guide versions so a different or calibrated judge can be swapped in.")
    if i in MT:
        L.append("- Hindi/Tamil probes are machine-translated by the same local 7B model (free, offline) and back-translated; a fidelity gate marks low-fidelity cells `n/a`. This is a heuristic, not a human-validated translation.")
    if i == "T7-007":
        L.append("- Counterfactual variants are generated from AgentCard skill examples and governance `fairness` (each "
                 "variant differs from its base only in the declared attribute tokens, validated). Four-fifths needs >= 3 runs per value.")
    if i in ("X-007", "X-006", "X-005"):
        L.append("- Budgets are fixed constants for the CPU-only reference box; adjust for your hardware.")
    L += ["", "## References", "", "Original sources this check derives from. The oracle itself is in-house deterministic code unless stated otherwise;"
          " papers and standards are cited as the source of the threat model or method, not as validation of this implementation.", ""]
    L += [f"{n}. {BIB[k]}" for n, k in enumerate(refs_for(i), 1)]
    return "\n".join(L) + "\n"


def main() -> None:
    """Write one markdown file per ID plus docs/tests/README.md index."""
    cat = catalogue()
    from agentest.standards import runner

    judge.configure("off", offline=True)  # the matrix is the judge-on verdict set, replayed from the bundled cache

    by: dict = {}
    for a, row in runner.run_all(mode="examples").items():
        for i, r in row.items():
            by.setdefault(i, {})[a] = r.status
    OUT.mkdir(parents=True, exist_ok=True)
    idx = [f"# Test reference ({len(ALL_IDS)} checks)", "", "| ID | what | doc |", "|:--|:--|:--|"]
    for i in ALL_IDS:
        (OUT / f"{i}.md").write_text(render(i, cat, by.get(i, {})))
        idx.append(f"| {i} | {what(i)[:90]} | [{i}.md]({i}.md) |")
    (OUT / "README.md").write_text("\n".join(idx) + "\n")
    print(f"wrote {len(ALL_IDS)} docs")


if __name__ == "__main__":
    main()
