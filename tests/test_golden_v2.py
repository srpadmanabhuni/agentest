"""Structure checks for the synthetic golden-v2 cases (golden/golden-cases-v2.jsonl and its CSV twin).

These tests read the data only. They do not run the checks and import nothing from the detector or judge code, so
they say nothing about the verdicts; they guard the shape of the data and that it stays separate from the locked agents.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "golden"
CASES = [json.loads(x) for x in (GOLDEN / "golden-cases-v2.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
CATALOGUE_IDS = {
    json.loads(x)["id"]
    for x in (ROOT / "catalog" / "checklist-110.jsonl").read_text(encoding="utf-8").splitlines()
    if x.strip()
}
FIELDS = {"agent_card", "case_id", "expected_verdict", "judge_answers", "label_provenance", "reason", "synthetic", "test_id", "tools", "traces"}


def test_every_test_id_has_exactly_one_pass_and_one_fail_case():
    got: dict[str, list[str]] = {}
    for c in CASES:
        got.setdefault(c["test_id"], []).append(c["expected_verdict"])
    assert len(got) == 38
    assert {t for t, v in got.items() if sorted(v) != ["fail", "pass"]} == set()
    assert len({c["case_id"] for c in CASES}) == len(CASES) == 76


def test_case_ids_follow_the_documented_pattern():
    for c in CASES:
        assert c["case_id"] == f"GC2-{c['test_id']}-{c['expected_verdict']}"


def test_test_ids_are_in_the_catalogue():
    assert {c["test_id"] for c in CASES} <= CATALOGUE_IDS


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_case_shape(case):
    assert set(case) == FIELDS
    assert case["expected_verdict"] in {"pass", "fail"}
    assert case["synthetic"] is True and case["label_provenance"] and case["reason"]
    assert isinstance(case["agent_card"], dict) and case["agent_card"].get("name")
    assert isinstance(case["tools"], dict) and isinstance(case["tools"].get("tools"), list)
    assert case["traces"] and all(isinstance(t, dict) and "resourceSpans" in t for t in case["traces"])
    for a in case["judge_answers"]:
        assert set(a) == {"guide", "payload", "answer"}


def test_csv_twin_matches_the_jsonl():
    with (GOLDEN / "golden-cases-v2.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert [r["case_id"] for r in rows] == [c["case_id"] for c in CASES]
    for r, c in zip(rows, CASES, strict=True):
        assert json.loads(r["record_json"]) == {k: c[k] for k in ("agent_card", "tools", "traces", "judge_answers")}
        assert (r["test_id"], r["expected_verdict"]) == (c["test_id"], c["expected_verdict"])
        assert int(r["n_traces"]) == len(c["traces"]) and int(r["n_judge_answers"]) == len(c["judge_answers"])


def test_cases_do_not_reuse_locked_agent_names():
    """The cases are a made-up desk. None may carry the id of an agent under agents/, whose traces and labels are locked."""
    locked = {p.name for p in (ROOT / "agents").iterdir() if p.is_dir()}
    assert locked, "agents/ is empty or missing"
    for c in CASES:
        text = json.dumps(c).lower()
        assert not any(f'"{a.lower()}"' in text or f"/{a.lower()}/" in text for a in locked), c["case_id"]
        assert c["agent_card"]["name"].lower() not in locked
