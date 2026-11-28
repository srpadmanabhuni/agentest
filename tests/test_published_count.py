"""The published test count is 165; README, --help and list must agree with the code."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from agentest.cli import build_parser, main
from agentest.standards.catalog import PUBLISHED_TEST_COUNT, published_ids

ROOT = Path(__file__).resolve().parents[1]


def test_code_published_total_is_165():
    ids = published_ids()
    assert PUBLISHED_TEST_COUNT == 165
    assert len(ids) == PUBLISHED_TEST_COUNT
    assert len(set(ids)) == PUBLISHED_TEST_COUNT


def test_readme_states_165():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"{PUBLISHED_TEST_COUNT} tests" in text
    # The lede and the "What it checks" heading must state 165, not another total.
    first = text.split("\n", 2)[2].split("\n\n", 1)[0]
    assert f"{PUBLISHED_TEST_COUNT} rule-based tests" in first
    assert re.search(rf"^{PUBLISHED_TEST_COUNT} tests\.", text, re.M)


def test_help_states_165():
    parser = build_parser()
    help_text = parser.format_help()
    assert f"{PUBLISHED_TEST_COUNT} tests" in help_text
    assert parser.description.startswith(
        f"Agentic AI Test Checklist: {PUBLISHED_TEST_COUNT} tests"
    )


def test_list_output_matches_published_ids(capsys):
    assert main(["list"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[-1] == f"{PUBLISHED_TEST_COUNT} test(s)"
    ids = [line.split()[0] for line in lines[:-1]]
    assert ids == list(published_ids())


def test_list_json_matches_published_ids(capsys):
    assert main(["list", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [r["id"] for r in rows] == list(published_ids())
    assert len(rows) == PUBLISHED_TEST_COUNT


@pytest.mark.parametrize(
    "path,needle",
    [
        ("src/agentest/__init__.py", f"{PUBLISHED_TEST_COUNT} tests"),
        ("pyproject.toml", f"{PUBLISHED_TEST_COUNT} deterministic"),
        ("CITATION.cff", f"{PUBLISHED_TEST_COUNT} tests"),
    ],
)
def test_other_surfaces_state_165(path, needle):
    text = (ROOT / path).read_text(encoding="utf-8")
    assert needle in text
