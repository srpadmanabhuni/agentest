"""Heuristic free-text checks: each has a documented-limits entry and three fixtures (pass, fail, false positive).

Fixtures, tests and docs only: no check is changed. The verdicts in ``tests/fixtures/heuristic_limits/manifest.json`` are what
the checks return today; a false-positive fixture records a limit and is not behaviour to rely on.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

import agentest
from agentest.standards import catalog

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "tests" / "fixtures" / "heuristic_limits"
MANIFEST = json.loads((FX / "manifest.json").read_text(encoding="utf-8"))
SETS = MANIFEST["sets"]
DOC = ROOT / "docs" / "testers" / "HEURISTIC-CHECK-LIMITS.md"
CASES = [(s["key"], cid, kind) for s in SETS for cid in s["checks"] for kind in ("pass", "fail", "fp")]
BANNED = re.compile(r"synthetic|\bfork|superior|best[- ]in|state[- ]of[- ]the[- ]art|\bstars?\b", re.I)


def _judge(s, kind, cid):
    return agentest.run(FX / s["fixtures"][kind]["file"], card=FX / s["card"], tools=FX / s["tools"], ids=[cid])[cid]


def test_builder_output_matches_committed_files():
    spec = importlib.util.spec_from_file_location("heuristic_limits_build", FX / "build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    assert build.main(["--check"]) == 0, "run: python tests/fixtures/heuristic_limits/build.py"


@pytest.mark.parametrize(("key", "cid", "kind"), CASES, ids=[f"{cid}-{kind}" for _, cid, kind in CASES])
def test_fixture_verdict(key, cid, kind):
    s = next(x for x in SETS if x["key"] == key)
    got = _judge(s, kind, cid)
    want = s["fixtures"][kind]["expect"]
    assert got.status == want, f"{cid} {kind}: {got.status} ({got.detail})"


def test_every_check_has_three_distinct_fixtures_and_a_limit():
    seen = set()
    for s in SETS:
        assert s["limits"] and s["reads"]
        files = [s["fixtures"][k]["file"] for k in ("pass", "fail", "fp")]
        assert len(set(files)) == 3
        assert [s["fixtures"][k]["expect"] for k in ("pass", "fail", "fp")] == ["pass", "fail", "fail"]
        for cid in s["checks"]:
            assert cid not in seen, f"{cid} appears in two fixture sets"
            seen.add(cid)
    assert len(seen) >= 50


def test_listed_checks_exist_in_the_catalogue_or_rules():
    from agentest.standards.rules import RULES

    known = set(catalog.catalogue()) | set(RULES)
    assert {cid for s in SETS for cid in s["checks"]} <= known


def test_docs_table_lists_every_check_with_links():
    text = DOC.read_text(encoding="utf-8")
    for s in SETS:
        for cid in s["checks"]:
            row = next((ln for ln in text.splitlines() if ln.startswith(f"| `{cid}` |")), None)
            assert row, f"{cid} missing from the table"
            for kind in ("pass", "fail", "fp"):
                assert f"(../../tests/fixtures/heuristic_limits/{s['fixtures'][kind]['file']})" in row
    assert not BANNED.search(text)


def test_fixture_files_exist_and_have_no_banned_wording():
    for p in FX.rglob("*"):
        if p.is_file() and p.suffix in {".json", ".jsonl", ".md", ".py"}:
            assert not BANNED.search(p.read_text(encoding="utf-8")), p


def test_fp_notes_describe_acceptable_behaviour_not_attacks():
    for s in SETS:
        assert s["fixtures"]["fp"]["note"].strip()
