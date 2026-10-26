"""The per-test framework crosswalk must stay in sync with the vendored catalogue.

`docs/FRAMEWORK-MAPPING-PER-TEST.md` is generated from the `control_refs` field of
`catalog/checklist-110.jsonl`. These tests fail if the document is edited by hand,
if the catalogue gains a reference that the document does not show, or if the
generator's vocabulary drifts from the tokens actually present in the data.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "FRAMEWORK-MAPPING-PER-TEST.md"


def _generator():
    """Import scripts/gen_framework_mapping.py as a module."""
    path = ROOT / "scripts" / "gen_framework_mapping.py"
    spec = importlib.util.spec_from_file_location("gen_framework_mapping", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_document_exists():
    assert DOC.is_file(), "docs/FRAMEWORK-MAPPING-PER-TEST.md is missing"


def test_document_is_up_to_date():
    gen = _generator()
    expected = gen.render(gen.load_rows())
    assert DOC.read_text(encoding="utf-8") == expected, (
        "docs/FRAMEWORK-MAPPING-PER-TEST.md is stale; run "
        "`PYTHONPATH=src python scripts/gen_framework_mapping.py`"
    )


def test_check_mode_passes():
    gen = _generator()
    assert gen.main(["--check"]) == 0


def test_every_catalogue_id_appears_in_the_table():
    gen = _generator()
    text = DOC.read_text(encoding="utf-8")
    for row in gen.load_rows():
        assert f"| **{row['id']}** |" in text, row["id"]


def test_every_token_in_the_data_has_a_documented_expansion():
    """No `_(no expansion recorded)_` placeholder may survive in the document."""
    gen = _generator()
    labels = {
        "NIST-AI-RMF": gen.NIST_LABELS,
        "ISO42001": gen.ISO_LABELS,
        "EU-AIA": gen.EU_LABELS,
        "OWASP-ASI": gen.ASI_LABELS,
    }
    for row in gen.load_rows():
        for fw, toks in gen.split_refs(row.get("control_refs", "")).items():
            for tok in toks:
                assert tok in labels[fw], f"{row['id']}: {fw} token {tok!r} has no expansion"
    assert "no expansion recorded" not in DOC.read_text(encoding="utf-8")


def test_control_refs_never_uses_numeric_asi_identifiers():
    """The catalogue uses descriptive ASI threat names, not OWASP ASIxx numbers.

    If this ever changes, the 'not OWASP identifiers' note in the generated
    document (and the EXPLAINABILITY-RESEARCH correction) must be revisited.
    """
    gen = _generator()
    import re

    for row in gen.load_rows():
        refs = row.get("control_refs", "")
        assert not re.search(r"ASI\d", refs), f"{row['id']} carries a numeric ASI id: {refs}"


def test_split_refs_handles_empty_and_malformed_values():
    gen = _generator()
    empty = gen.split_refs("")
    assert all(v == [] for v in empty.values())
    assert gen.split_refs("NIST-AI-RMF:MEASURE-2.3")["NIST-AI-RMF"] == ["MEASURE-2.3"]
    # unknown framework and tokenless entries are ignored rather than crashing
    assert all(v == [] for v in gen.split_refs("BOGUS:x;NIST-AI-RMF").values())


def test_split_refs_deduplicates_tokens():
    gen = _generator()
    refs = gen.split_refs("EU-AIA:Art9;EU-AIA:Art9")
    assert refs["EU-AIA"] == ["Art9"]


def test_class_level_doc_is_linked_from_the_per_test_doc():
    """The two crosswalks should point at each other so a reader finds both."""
    per_test = DOC.read_text(encoding="utf-8")
    assert "FRAMEWORK-MAPPING.md" in per_test
    class_level = (ROOT / "docs" / "FRAMEWORK-MAPPING.md").read_text(encoding="utf-8")
    assert "FRAMEWORK-MAPPING-PER-TEST.md" in class_level
