"""Golden cases v2: one synthetic pass case and one fail case per assessable core test, re-derived by the checks.

The cases (golden/golden-cases-v2.jsonl) are rebuilt from golden/build_golden_v2.py; judge questions are answered only
from the hand-written labels stored with each case (offline replay, nothing is sent anywhere)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from agentest.standards import judge

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "golden"
CASES = [json.loads(x) for x in (GOLDEN / "golden-cases-v2.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
ASSESSABLE = json.loads((ROOT / "fixtures" / "core-assessable.json").read_text(encoding="utf-8"))["assessable"]


def _load(name: str):
    sys.path.insert(0, str(GOLDEN))
    try:
        spec = importlib.util.spec_from_file_location(name, GOLDEN / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(GOLDEN))


@pytest.fixture
def isolated_judge(monkeypatch):
    saved = (judge._ACTIVE, judge._CONFIGURED, judge._ACTIVE2, judge._CONFIGURED2)
    monkeypatch.setenv("AGENTEST_JUDGE_NO_BUNDLED", "1")
    yield
    judge._ACTIVE, judge._CONFIGURED, judge._ACTIVE2, judge._CONFIGURED2 = saved


def test_every_assessable_core_test_has_a_pass_and_a_fail_case():
    got: dict[str, set] = {}
    for c in CASES:
        got.setdefault(c["test_id"], set()).add(c["expected_verdict"])
    assert {t for t in ASSESSABLE if got.get(t) != {"pass", "fail"}} == set()
    assert set(got) <= set(ASSESSABLE)
    assert len({c["case_id"] for c in CASES}) == len(CASES)


def test_cases_are_synthetic():
    blind = {f"a{i}" for i in range(161, 171)}
    for c in CASES:
        assert c["synthetic"] is True and c["label_provenance"]
        text = json.dumps(c).lower()
        assert not any(f'"{b}"' in text or f"/{b}/" in text for b in blind), c["case_id"]


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_checks_reproduce_the_golden_verdict(case, isolated_judge):
    chk = _load("check_golden_v2")
    status, detail = chk.verdict(case)
    assert status == case["expected_verdict"], detail


def test_file_matches_the_builder(isolated_judge):
    b = _load("build_golden_v2")
    assert [json.dumps(c, sort_keys=True, ensure_ascii=False) for c in b.build()] == \
        [json.dumps(c, sort_keys=True, ensure_ascii=False) for c in CASES]
