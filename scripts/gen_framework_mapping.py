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

FRAMEWORKS = ["NIST-AI-RMF", "EU-AIA", "OWASP-ASI"]

# Human-readable expansion of the tokens used in control_refs (catalogue v1.3.1).
NIST_LABELS = {
    "MEASURE": "MEASURE function: system performance, security and fairness evaluated against stated claims",
    "MANAGE": "MANAGE function: risks prioritised, treated and monitored, incidents responded to",
    "GOVERN": "GOVERN function: roles, responsibilities and accountability structures",
}
EU_LABELS = {
    "Art9": "Art. 9: risk management system",
    "Art14": "Art. 14: human oversight",
}
# OWASP Top 10 for Agentic Applications 2026 (Agentic Security Initiative). Only the
# identifiers that appear in the catalogue need an entry; the test suite checks that.
ASI_LABELS = {
    "ASI01": "ASI01: Agent Goal Hijack",
    "ASI02": "ASI02: Tool Misuse and Exploitation",
    "ASI03": "ASI03: Identity and Privilege Abuse",
    "ASI04": "ASI04: Agentic Supply Chain Vulnerabilities",
    "ASI05": "ASI05: Unexpected Code Execution (RCE)",
    "ASI06": "ASI06: Memory and Context Poisoning",
    "ASI07": "ASI07: Insecure Inter-Agent Communication",
    "ASI08": "ASI08: Cascading Failures",
    "ASI09": "ASI09: Human-Agent Trust Exploitation",
    "ASI10": "ASI10: Rogue Agents",
}
LABELS = {"NIST-AI-RMF": NIST_LABELS, "EU-AIA": EU_LABELS, "OWASP-ASI": ASI_LABELS}


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
        "Tokens are copied from the catalogue. The expansions below say what each token refers to; "
        "they are orientation aids, not clause-level citations.",
        "",
    ]
    for f, note in (
        ("NIST-AI-RMF", "NIST AI RMF 1.0 functions. The catalogue records the function, not a subcategory."),
        ("EU-AIA", "Regulation (EU) 2024/1689 articles."),
        ("OWASP-ASI", "OWASP Top 10 for Agentic Applications 2026 identifiers."),
    ):
        L += [f"**`{f}`**: {note}", "", "| Token | Meaning | IDs |", "|:--|:--|--:|"]
        for tok, n in sorted(tok_counts[f].items()):
            L.append(f"| `{tok}` | {LABELS[f].get(tok, '_(no expansion recorded)_')} | {n} |")
        L.append("")

    # ---- per-test table
    L += [
        "## Per-test crosswalk",
        "",
        "| ID | Class | Severity | NIST AI RMF | EU AI Act | OWASP agentic |",
        "|:--|:--|:--|:--|:--|:--|",
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

    # ---- gaps (all figures computed from the data)
    missing = {f: [r["id"] for r in rows if not split_refs(r.get("control_refs", ""))[f]] for f in FRAMEWORKS}
    none_at_all = [r["id"] for r in rows if not any(split_refs(r.get("control_refs", "")).values())]

    def by_class(ids: list[str]) -> str:
        return ", ".join(f"{c} ({n})" for c, n in sorted(Counter(i.split("-")[0] for i in ids).items()))

    def ids_md(ids: list[str]) -> str:
        return ", ".join(f"`{i}`" for i in ids) if ids else "none"

    nist_toks = ", ".join(f"`{t}`" for t in sorted(tok_counts["NIST-AI-RMF"]))
    eu_toks = ", ".join(f"`{t}`" for t in sorted(tok_counts["EU-AIA"]))
    asi_used = ", ".join(f"`{t}`" for t in sorted(tok_counts["OWASP-ASI"]))
    asi_unused = ", ".join(f"`{t}`" for t in ASI_LABELS if t not in tok_counts["OWASP-ASI"])

    L += [
        "",
        "## Gaps and open questions",
        "",
        "These are recorded so a reviewer can act on them, not hidden behind a filled-in cell. "
        "Every figure is computed from the catalogue when the page is generated.",
        "",
        "### NIST AI RMF",
        "",
        f"{len(missing['NIST-AI-RMF'])} IDs carry no `NIST-AI-RMF` token ({by_class(missing['NIST-AI-RMF'])}): "
        + ids_md(missing["NIST-AI-RMF"])
        + f". The tokens in use are {nist_toks}; the catalogue does not assert a MAP reference for any ID, "
        "and the catalogue records functions, not subcategories.",
        "",
        "### EU AI Act",
        "",
        f"{len(missing['EU-AIA'])} of {total} IDs carry no `EU-AIA` token, and the ones that do use only {eu_toks}. "
        "This is the expected shape rather than an error: the Act's high-risk requirements only apply "
        "to systems in scope, and most checklist IDs describe failure modes that exist regardless of "
        "regulatory classification.",
        "",
        "### OWASP agentic identifiers",
        "",
        f"{len(missing['OWASP-ASI'])} of {total} IDs carry no `OWASP-ASI` token ({by_class(missing['OWASP-ASI'])}). "
        f"The identifiers in use are {asi_used}. Not asserted for any ID: {asi_unused}.",
        "",
        "### Whole catalogue",
        "",
        f"IDs with no reference to any of the three frameworks: {ids_md(none_at_all)}.",
        "",
        "A blank cell is a statement that no mapping is asserted. Where a test's relationship to a "
        "framework is arguable, an empty cell is more honest than an invented clause number.",
        "",
        "## Sources",
        "",
        "- NIST (2023). AI 100-1 *Artificial Intelligence Risk Management Framework (AI RMF 1.0).* "
        "[doi:10.6028/NIST.AI.100-1](https://doi.org/10.6028/NIST.AI.100-1)",
        "- Regulation (EU) 2024/1689 (Artificial Intelligence Act). "
        "<https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng>",
        "- OWASP GenAI Security Project. *OWASP Top 10 for Agentic Applications 2026.* "
        "<https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/>",
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
