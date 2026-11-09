"""v3.4: no regular expression decides a verdict on natural language. Every pattern in rules.py is a declared machine-
format validator or a pre-filter (scripts/regex_final_count.py); the count of regex-final checks must stay 0."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import regex_final_count as R  # noqa: E402


def test_regex_final_count_is_zero():
    paths = [R.RULES, R.PACKS, *sorted((R.ROOT / "src/agentest/standards/detectors").glob("*.py"))]
    final = []
    for path in paths:
        if path.exists():
            final += [f"{path.name}: {item}" for item in R.scan(path)["regex_final"]]
    assert not final, final


def test_every_compiled_pattern_is_classified_and_declared():
    r = R.scan()
    assert r["compiled"] == len(r["format_validators"]) + len(r["prefilters"])
    assert not r["declared_but_missing"], r["declared_but_missing"]
