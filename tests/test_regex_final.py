"""v3.4: no regular expression decides a verdict on natural language. Every pattern in rules.py is a declared machine-
format validator or a pre-filter (scripts/regex_final_count.py); the count of regex-final checks must stay 0."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import regex_final_count as R  # noqa: E402


def test_regex_final_count_is_zero():
    r = R._merge([(p, R.scan(p)) for p in R.modules()])
    assert r["regex_final_count"] == 0, r["regex_final"]


def test_every_compiled_pattern_is_classified_and_declared():
    for path in R.modules():
        r = R.scan(path)
        assert r["compiled"] == len(r["format_validators"]) + len(r["prefilters"]), path
        assert not r["declared_but_missing"], (path, r["declared_but_missing"])
        assert r["regex_final_count"] == 0, (path, r["regex_final"])
