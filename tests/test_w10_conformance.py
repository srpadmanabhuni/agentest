"""Synthetic conformance suite for the assessable core tests.

Fixtures live in tests/fixtures/w10_conformance/. Detector logic is not under test for edits;
a verdict that disagrees with the fixture is an expected failure only when xfails.json says so.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
from pathlib import Path

import pytest

from agentest.standards.rules import NA, Ctx, _t2_014
from tests.fixtures.w10_conformance.suite import (
    ASSESSABLE,
    LANG_TESTS,
    VOCAB,
    _agent,
    all_fixtures,
    coverage_rows,
    verdict,
    xfail_reason,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "w10_conformance"
ROUND_ID = re.compile(r"(?<![\w.-])(?:[Aa]\d{2,3}|c\d+-\d+|conv-\d+|cf_gender|(?:kn|bn|hi|ta)-big)(?![\w-])")


def _guard():
    path = ROOT / "scripts" / "agent_vocab_guard.py"
    spec = importlib.util.spec_from_file_location("agent_vocab_guard", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("row", all_fixtures(), ids=lambda row: row["id"])
def test_w10_fixture_verdict(row):
    status, detail = verdict(row["case"], row["vocabulary"], row["dialect"])
    reason = xfail_reason(row["id"])
    if status != row["expect"]:
        if reason:
            pytest.xfail(f"{reason} (got {status})")
        pytest.fail(f"{row['id']}: {status} != {row['expect']}: {detail}")
    assert not reason, f"{row['id']} is listed as xfail but the verdict matches"


def test_t2_014_rule_is_na_without_a_trace():
    """evaluate() reports not-run when no trace exists. The timestamp rule itself is n/a."""
    agent = _agent(VOCAB["shelf"], {}, "standard")
    with pytest.raises(NA, match="no runs"):
        _t2_014(Ctx(agent, [], "examples"), "T2-014")


def test_historical_130_and_locked_checks_have_pass_and_fail():
    from agentest.standards.catalog import CATALOGUE_IDS, X_IDS

    historical = list(CATALOGUE_IDS) + [item for item in X_IDS if item <= "X-020"]
    flags: dict[str, set[str]] = {}
    for row in all_fixtures():
        if row["expect"] in ("pass", "fail"):
            flags.setdefault(row["test"], set()).add(row["expect"])
    missing = [test for test in historical if flags.get(test, set()) != {"pass", "fail"}]
    assert not missing, missing
    locked = json.loads((FIXTURE_DIR / "locked.json").read_text())
    gaps = sorted(test for test, item in locked.items() if item.get("source") == "gap")
    uncovered = [test for test, kinds in flags.items() if kinds != {"pass", "fail"}]
    assert not uncovered
    assert set(gaps).isdisjoint(flags)


def test_every_in_scope_test_has_the_required_matrix():
    rows = coverage_rows()
    assert [row["test"] for row in rows] == list(ASSESSABLE)
    assert len(rows) == 38
    for row in rows:
        assert row["fixtures"] >= 10, row["test"]
        assert row["dialects"] == ["langgraph", "otlp"], row
        assert row["vocabularies"] == ["clinic", "shelf"], row
        expects = set(row["expects"])
        assert {"pass", "fail"} <= expects, row
        if row["test"] == "T2-014":
            assert "not-run" in expects
        else:
            assert "n/a" in expects, row
        if row["test"] in LANG_TESTS:
            assert {"hi", "ta"} <= set(row["languages"]), row


def test_fixtures_do_not_use_round_ids():
    bad = []
    for path in FIXTURE_DIR.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".json"}:
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            for match in ROUND_ID.finditer(line):
                bad.append(f"{path.relative_to(ROOT)}:{lineno}: {match.group(0)}")
    assert not bad, bad


def test_xfail_notes_name_real_fixtures():
    data = json.loads((FIXTURE_DIR / "xfails.json").read_text())
    assert isinstance(data, dict)
    known = {row["id"] for row in all_fixtures()}
    unknown = sorted(set(data) - known)
    assert not unknown, unknown
    for note in data.values():
        assert isinstance(note, str) and note.strip()


def test_vocab_guard_flags_round_case_ids():
    guard = _guard()
    planted = " ".join(["c6" + "-3", "conv" + "-2", "kn" + "-big", "cf" + "_gender"])
    assert guard.round_case_hits("src/agentest/standards/rules.py", planted) == ["c6-3", "conv-2", "kn-big", "cf_gender"]
    assert guard.round_case_hits("src/agentest/standards/rules.py", "def _cf_sig():") == []
    assert guard.round_case_hits("tests/test_w10_conformance.py", planted) == []


def test_conformance_coverage_section_lists_every_test():
    path = ROOT / "scripts" / "conformance_coverage.py"
    spec = importlib.util.spec_from_file_location("conformance_coverage", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    text = mod.render_section()
    for test in ASSESSABLE:
        assert f"| {test} |" in text
    # the section is a fixture inventory, not a score report
    tree = ast.parse(path.read_text())
    assert isinstance(tree, ast.Module)
