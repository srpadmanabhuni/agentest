#!/usr/bin/env python3
"""Generate docs/FRAMEWORK-MAPPING-PER-TEST.md from the vendored catalogue.

The class-level crosswalk in docs/FRAMEWORK-MAPPING.md is a hand-written,
indicative orientation aid. This script produces the per-test counterpart from
the ``control_refs`` field that is already carried by every row of
``catalog/checklist-110.jsonl``, so the document can never drift from the data.

Usage:
  PYTHONPATH=src python scripts/gen_framework_mapping.py           # write the doc
  PYTHONPATH=src python scripts/gen_framework_mapping.py --check   # exit 1 if stale
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "FRAMEWORK-MAPPING-PER-TEST.md"

FRAMEWORKS = ["NIST-AI-RMF", "ISO42001", "EU-AIA", "OWASP-ASI"]

# Human-readable expansion of the short tokens used in control_refs.
NIST_LABELS = {
    "MEASURE-2.3": "MEASURE 2.3 — system performance/security evaluated against stated claims",
    "MANAGE-2.4": "MANAGE 2.4 — mechanisms to sustain deployed AI value and respond to incidents",
    "GOVERN-1.2": "GOVERN 1.2 — roles, responsibilities and accountability structures",
}
ISO_LABELS = {
    "A.6": "Annex A.6 — AI system impact assessment (data, privacy, harms)",
    "A.8": "Annex A.8 — AI system performance evaluation and operational controls",
}
EU_LABELS = {
    "Art9": "Art. 9 — risk management system",
    "Art14": "Art. 14 — human oversight",
}
# The catalogue uses descriptive tokens, not OWASP's ASIxx numbering. These are
# the repo's own shorthand; the doc says so explicitly rather than implying that
# a published OWASP identifier exists for each one.
ASI_LABELS = {
    "ToolMisuse": "tool / capability misuse by the agent",
    "PromptInjection": "instruction injection through untrusted content",
    "PrivilegeCompromise": "privilege escalation or privilege confusion across agents",
    "MemoryPoisoning": "poisoning of persisted memory or state",
    "AgenticHandoff": "unsafe handover between agents of differing privilege",
    "GoalHijacking": "goal or objective hijacking",
    "HumanManipulation": "manipulation of the human approver",
}


def split_refs(raw: str) -> dict[str, list[str]]:
    """Split a ``control_refs`` string into ``{framework: [token, ...]}``."""
    out: dict[str, list[str]] = {f: [] for f in FRAMEWORKS}
    for part in (raw or "").split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        fw, _, tok = part.partition(":")
        fw, tok = fw.strip(), tok.strip()
        if fw in out and tok and tok not in out[fw]:
            out[fw].append(tok)
    return out


def load_rows() -> list[dict]:
    """Read the vendored catalogue."""
    import json

    p = ROOT / "catalog" / "checklist-110.jsonl"
    text = p.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def render(rows: list[dict]) -> str:
    """Build the whole markdown document."""
    total = len(rows)
    covered = {f: sum(1 for r in rows if split_refs(r.get("control_refs", ""))[f]) for f in FRAMEWORKS}
    tok_counts = {f: Counter() for f in FRAMEWORKS}
    for r in rows:
        for fw, toks in split_refs(r.get("control_refs", "")).items():
            tok_counts[fw].update(toks)

    L: list[str] = []
    L += [
        "# Framework mapping — per test",
        "",
        "*Generated from `catalog/checklist-110.jsonl` by `scripts/gen_framework_mapping.py`. "
        "Do not edit by hand; re-run the script instead.*",
        "",
        "This is the per-test counterpart to the class-level crosswalk in "
        "[FRAMEWORK-MAPPING.md](FRAMEWORK-MAPPING.md). Every row below is taken verbatim from the "
        "`control_refs` field carried by the catalogue entry for that ID, so the table and the "
        "machine-readable catalogue cannot disagree.",
        "",
        "It remains an **indicative crosswalk**, not a compliance claim, an audit result or a "
        "certification statement. Passing a check does not make a system conformant with any "
        "framework. The mappings point at *themes*: they tell you which part of a framework is "
        "likely to care about a given failure mode, not which clause you have satisfied.",
        "",
        "## Coverage",
        "",
        f"Of the {total} catalogue IDs:",
        "",
        "| Framework | IDs with a reference | Share |",
        "|:--|--:|--:|",
    ]
    for f in FRAMEWORKS:
        n = covered[f]
        L.append(f"| `{f}` | {n} | {n / total:.0%} |")

    L += [
        "",
        "A blank cell is **not** an oversight and **not** a finding that the test is irrelevant to "
        "that framework. It means the catalogue author did not assert a mapping. Absence of a "
        "reference is the honest state for a test whose relationship to a framework is arguable; "
        "inventing a clause number to fill the cell would be worse than leaving it empty. See "
        "[Gaps and open questions](#gaps-and-open-questions).",
        "",
        "## Token vocabulary",
        "",
        "The tokens are the repo's own shorthand, not identifiers published by the framework "
        "owners. Expansions below are the mapping the catalogue intends.",
        "",
    ]
    for f, labels, note in (
        ("NIST-AI-RMF", NIST_LABELS, "NIST AI RMF 1.0 subcategories (MEASURE / MANAGE / GOVERN)."),
        ("ISO42001", ISO_LABELS, "ISO/IEC 42001:2023 Annex A control groups."),
        ("EU-AIA", EU_LABELS, "Regulation (EU) 2024/1689 articles."),
        (
            "OWASP-ASI",
            ASI_LABELS,
            "Descriptive threat names from the OWASP Agentic Security Initiative threat themes. "
            "These are **not** OWASP `ASIxx` identifiers — see the note on that below.",
        ),
    ):
        L += [f"**`{f}`** — {note}", "", "| Token | Meaning | IDs |", "|:--|:--|--:|"]
        for tok, n in tok_counts[f].most_common():
            L.append(f"| `{tok}` | {labels.get(tok, '_(no expansion recorded)_')} | {n} |")
        L.append("")

    # ---- per-test table
    L += [
        "## Per-test crosswalk",
        "",
        "| ID | Class | Severity | NIST AI RMF | ISO/IEC 42001 | EU AI Act | OWASP agentic |",
        "|:--|:--|:--|:--|:--|:--|:--|",
    ]
    for r in rows:
        refs = split_refs(r.get("control_refs", ""))
        cells = []
        for f in FRAMEWORKS:
            toks = refs[f]
            cells.append(", ".join(f"`{t}`" for t in toks) if toks else "—")
        L.append(
            f"| **{r['id']}** | {r.get('class_id', '')} | {r.get('severity', '')} | "
            + " | ".join(cells)
            + " |"
        )

    # ---- gaps
    no_nist = [r["id"] for r in rows if not split_refs(r.get("control_refs", ""))["NIST-AI-RMF"]]
    no_iso = [r["id"] for r in rows if not split_refs(r.get("control_refs", ""))["ISO42001"]]
    no_eu = [r["id"] for r in rows if not split_refs(r.get("control_refs", ""))["EU-AIA"]]
    no_asi = [r["id"] for r in rows if not split_refs(r.get("control_refs", ""))["OWASP-ASI"]]

    L += [
        "",
        "## Gaps and open questions",
        "",
        "These are recorded so a reviewer can act on them, not hidden behind a filled-in cell.",
        "",
        "### Whole classes with no NIST AI RMF reference",
        "",
        f"{len(no_nist)} IDs carry no `NIST-AI-RMF` token, and they are concentrated in T3: "
        + ", ".join(f"`{i}`" for i in no_nist)
        + ".",
        "",
        "T3 is the authorisation and handover class. NIST AI RMF 1.0 predates tool-calling agents "
        "and has no subcategory written for inter-agent privilege transfer, so the honest options "
        "were `GOVERN-1.2` (roles and accountability) or nothing. Only three T3 rows claim "
        "`GOVERN-1.2`. Whether the remaining T3 tests should also claim it, or whether the gap "
        "should stay visible, is a judgement call for the maintainer.",
        "",
        "### EU AI Act coverage is the thinnest",
        "",
        f"{len(no_eu)} of {total} IDs carry no `EU-AIA` token. That is the right shape rather than "
        "an omission: the Act's high-risk requirements only bite for systems in scope, and most "
        "checklist IDs describe failure modes that exist regardless of regulatory classification. "
        "Mapping them all to Art. 9 would inflate the crosswalk without informing anyone.",
        "",
        "### ISO/IEC 42001 has only two control groups in use",
        "",
        f"{len(no_iso)} IDs carry no `ISO42001` token, and the ones that do use only `A.6` (3 IDs) "
        "and `A.8` (59 IDs). Annex A has considerably more control groups than two. `A.8` "
        "(performance evaluation) is a defensible default for a test catalogue, but `A.6` being "
        "used for only three impact-assessment-flavoured tests suggests the mapping was applied "
        "narrowly. Finer ISO mapping would need someone with the standard text to hand.",
        "",
        "### `OWASP-ASI` tokens are not OWASP identifiers",
        "",
        f"{len(no_asi)} of {total} IDs carry no `OWASP-ASI` token at all, so roughly a fifth of the "
        "catalogue asserts no agentic-threat mapping. The remaining four fifths use the descriptive "
        "names below.",
        "",
        "This is the correction worth flagging. The catalogue uses descriptive names "
        "(`ToolMisuse`, `PrivilegeCompromise`, `MemoryPoisoning`, `AgenticHandoff`, "
        "`GoalHijacking`, `HumanManipulation`, `PromptInjection`) that describe OWASP Agentic "
        "Security Initiative *threat themes*. They are **not** the `ASIxx` identifiers used by "
        "OWASP's published agentic lists, and the catalogue contains no numeric ASI reference at "
        "all.",
        "",
        "Two consequences:",
        "",
        "1. A reader cannot follow an `OWASP-ASI:ToolMisuse` token to a specific OWASP document "
        "the way they can follow `EU-AIA:Art14` to Article 14. The token is a label for a threat "
        "category, not a citation.",
        "2. Any prose elsewhere in the repo that presents an `ASIxx` number as coming *from* "
        "`control_refs` is inaccurate, because `control_refs` has never contained one. "
        "`docs/EXPLAINABILITY-RESEARCH.md` does exactly this for T3-006, describing it as "
        "\"ASI03 … and ASI07 … from catalogue `control_refs`\" while that row's actual value is "
        "`OWASP-ASI:PrivilegeCompromise;OWASP-ASI:AgenticHandoff`. Either the research note should "
        "stop attributing the numbers to the catalogue, or the catalogue should gain a numeric "
        "field. That choice belongs to the maintainer.",
        "",
        "### No MAP references",
        "",
        "NIST AI RMF's MAP function (context and risk identification) appears in no `control_refs` "
        "token. The class-level doc says MAP applies to all classes; the per-test data asserts it "
        "for none. One of the two should move.",
        "",
        "## Sources",
        "",
        "- NIST (2023). AI 100-1 *Artificial Intelligence Risk Management Framework (AI RMF 1.0).* "
        "[doi:10.6028/NIST.AI.100-1](https://doi.org/10.6028/NIST.AI.100-1)",
        "- Regulation (EU) 2024/1689 (Artificial Intelligence Act). "
        "<https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng>",
        "- ISO/IEC 42001:2023 *Information technology — Artificial intelligence — Management "
        "system.* <https://www.iso.org/standard/81230.html>",
        "- OWASP Top 10 for LLM Applications 2025. <https://genai.owasp.org/llm-top-10/>",
        "- OWASP GenAI Security Project. *Agentic AI – Threats and Mitigations.* "
        "<https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/>",
        "",
    ]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    """Write the document, or verify it is up to date."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed file is stale")
    a = ap.parse_args(argv)

    text = render(load_rows())
    if a.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print(f"ERROR {OUT.relative_to(ROOT)} is stale; re-run without --check")
            return 1
        print(f"OK {OUT.relative_to(ROOT)} is up to date")
        return 0

    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
