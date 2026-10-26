#!/usr/bin/env python3
"""Generate docs/tests/<ID>.md for all 130 checks from the vendored catalogue,
the profiles (expectations and method notes) and the committed results.json.

Usage: PYTHONPATH=src python scripts/gen_test_docs.py
"""

from __future__ import annotations

import json
from pathlib import Path

from agentest.model.generic import CHECKS
from agentest.model.profile import load_all
from agentest.real.ids import ALL_IDS, X_IDS, catalogue, what
from agentest.refs import BIB, refs_for

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "tests"
PROFILES = load_all()
HEUR = {"T7-004", "T7-005", "T7-012", "T4-005", "X-003", "X-009", "X-011", "X-012", "X-013", "X-014", "X-015", "X-016", "X-018"}
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
    L += ["## Preconditions", "", "- `pip install -e \".[dev]\"`; no network, no API key, no model needed for replay.",
          "- Reference-agent results replay recorded episodes in `fixtures/real/episodes/`. Re-recording needs the local 7B GGUF (see GUIDEBOOK.md, Recording).", ""]
    samples = [a for a, p in PROFILES.items() if p.adapter == "sample"]
    refs = [a for a, p in PROFILES.items() if p.adapter != "sample" and (i in p.expect or res.get(a, "n/a") != "n/a")]
    L += ["## How it is judged (v2, model-driven)", "",
          "Every verdict comes from the generic engine over the standard trace and the agent's profile. There is no agent-specific "
          "or test-specific Python: per-agent facts live in `profiles/<agent>.yaml`, shared expectations in `profiles/_lib/*.yaml`.", ""]
    lib = PROFILES[samples[0]] if samples else None
    if lib and i in lib.expect:
        L += [f"**Sample agents ({len(samples)}):** expectation from `profiles/_lib/samples.yaml`, evaluated over the recorded scenario snapshot:", ""]
        L += _block(lib.expect[i])
        if lib.expect_notes.get(i):
            L += ["Method notes:", "", "\n".join("> " + x for x in lib.expect_notes[i].splitlines()), ""]
    if i in CHECKS:
        L += [f"**Built-in generic check (default when a profile states no expectation):** {CHECKS[i][0]}", ""]
    if refs:
        L += ["**Reference agents:**", ""]
        for a in refs:
            p = PROFILES[a]
            if i in p.expect:
                L += [f"`{a}` ({p.framework}): profile expectation" + ":", ""]
                L += _block(p.expect[i])
            else:
                L += [f"`{a}` ({p.framework}): built-in generic check over the profile-declared surface.", ""]
    else:
        L += ["**Reference agents:** no reference agent exposes this surface; cells report `n/a`.", ""]
    L += ["## How to run", "", "```bash", f"agentest real --ids {i}                 # every profiled agent, offline replay",
          f"agentest real --ids {i} --agents reference", "```", ""]
    L += ["## How to interpret", "", "- `pass`: the oracle held on every recorded episode for that agent.", "- `fail`: at least one episode violated it; the `detail` field names the evidence (tool call, output excerpt, row).",
          "- `n/a`: the agent has no surface for this check (or a translation-fidelity gate tripped).", ""]
    if res:
        cnt = {s: sum(1 for v in res.values() if v == s) for s in ("pass", "fail", "n/a")}
        L += [f"Current matrix: {cnt['pass']} pass · {cnt['fail']} fail · {cnt['n/a']} n/a across {len(res)} agents.", "",
              "| agent | status |", "|:--|:--|"] + [f"| {a} | {s} |" for a, s in res.items()] + [""]
    L += ["## Known limits", "", "- Small k (1–3 runs per probe); a pass is evidence, not proof.",
          "- Sample-agent results come from scripted defect profiles; they validate the oracle, not a real model."]
    if i in HEUR:
        L.append("- Uses a regex/keyword heuristic over free text: an **uncalibrated heuristic**, expect false positives/negatives.")
    if i in MT:
        L.append("- Hindi/Tamil probes are machine-translated by the same local 7B model (free, offline) and back-translated; a fidelity gate marks low-fidelity cells `n/a`. This is a heuristic, not a human-validated translation.")
    if i in ("X-007", "X-006", "X-005"):
        L.append("- Budgets are fixed constants for the CPU-only reference box; adjust for your hardware.")
    L += ["", "## References", "", "Original sources this check derives from. The oracle itself is in-house deterministic code unless stated otherwise;"
          " papers and standards are cited as the source of the threat model or method, not as validation of this implementation.", ""]
    L += [f"{n}. {BIB[k]}" for n, k in enumerate(refs_for(i), 1)]
    return "\n".join(L) + "\n"


def main() -> None:
    """Write one markdown file per ID plus docs/tests/README.md index."""
    cat = catalogue()
    data = json.loads((ROOT / "fixtures" / "real" / "results.json").read_text())
    by = {}
    for a, row in data.items():
        for i, r in row.items():
            by.setdefault(i, {})[a] = r["status"] if isinstance(r, dict) else r
    OUT.mkdir(parents=True, exist_ok=True)
    idx = ["# Test reference (130 checks)", "", "| ID | what | doc |", "|:--|:--|:--|"]
    for i in ALL_IDS:
        (OUT / f"{i}.md").write_text(render(i, cat, by.get(i, {})))
        idx.append(f"| {i} | {what(i)[:90]} | [{i}.md]({i}.md) |")
    (OUT / "README.md").write_text("\n".join(idx) + "\n")
    print(f"wrote {len(ALL_IDS)} docs")


if __name__ == "__main__":
    main()
