"""Structure checks for the golden-v2 use-case records (golden/golden-cases-v2.jsonl and its CSV twin).

These tests read the data only. They do not run the checks and import nothing from the detector or judge code, so
they say nothing about the verdicts; they guard the shape of the data and that it stays separate from the locked agents.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

LEGACY_USE_CASE_KEY = "synthetic"
USE_CASE_KEY = "use_case"


def use_case_flag(record):
    """Return the use-case flag, accepting the legacy `synthetic` key.

    If both keys are present, `use_case` wins. A missing flag raises KeyError.
    """
    if USE_CASE_KEY in record:
        return bool(record[USE_CASE_KEY])
    if LEGACY_USE_CASE_KEY in record:
        return bool(record[LEGACY_USE_CASE_KEY])
    raise KeyError(f"record has neither {USE_CASE_KEY!r} nor {LEGACY_USE_CASE_KEY!r}")


def csv_use_case_value(row):
    """Read the use-case column from a CSV row, accepting the legacy header."""
    if USE_CASE_KEY in row and row[USE_CASE_KEY] not in (None, ""):
        return str(row[USE_CASE_KEY])
    if LEGACY_USE_CASE_KEY in row and row[LEGACY_USE_CASE_KEY] not in (None, ""):
        return str(row[LEGACY_USE_CASE_KEY])
    raise KeyError(f"CSV row has neither {USE_CASE_KEY!r} nor {LEGACY_USE_CASE_KEY!r}")


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "golden"
CASES = [json.loads(x) for x in (GOLDEN / "golden-cases-v2.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
CATALOGUE_IDS = {
    json.loads(x)["id"]
    for x in (ROOT / "catalog" / "checklist-110.jsonl").read_text(encoding="utf-8").splitlines()
    if x.strip()
}
FIELDS = {"agent_card", "case_id", "expected_verdict", "judge_answers", "label_provenance", "reason", "use_case", "test_id", "tools", "traces"}


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
    assert use_case_flag(case) is True and case["label_provenance"] and case["reason"]
    assert LEGACY_USE_CASE_KEY not in case
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
        assert csv_use_case_value(r) == "true"
        assert LEGACY_USE_CASE_KEY not in r


def test_use_case_flag_accepts_legacy_synthetic_key():
    """Old records that still use the `synthetic` key are read and accepted."""
    modern = {"use_case": True, "case_id": "legacy-modern"}
    legacy = {"synthetic": True, "case_id": "legacy-old"}
    both = {"use_case": True, "synthetic": False, "case_id": "legacy-both"}
    assert use_case_flag(modern) is True
    assert use_case_flag(legacy) is True
    assert use_case_flag(both) is True  # canonical key wins
    with pytest.raises(KeyError):
        use_case_flag({"case_id": "missing"})


def test_csv_reader_accepts_legacy_synthetic_header():
    row = {"case_id": "GC2-legacy", "synthetic": "true"}
    assert csv_use_case_value(row) == "true"
    assert csv_use_case_value({"case_id": "GC2-new", "use_case": "true"}) == "true"
    with pytest.raises(KeyError):
        csv_use_case_value({"case_id": "GC2-missing"})


def test_cases_do_not_reuse_locked_agent_names():
    """The cases are a made-up desk. None may carry the id of an agent under agents/, whose traces and labels are locked."""
    locked = {p.name for p in (ROOT / "agents").iterdir() if p.is_dir()}
    assert locked, "agents/ is empty or missing"
    for c in CASES:
        text = json.dumps(c).lower()
        assert not any(f'"{a.lower()}"' in text or f"/{a.lower()}/" in text for a in locked), c["case_id"]
        assert c["agent_card"]["name"].lower() not in locked
