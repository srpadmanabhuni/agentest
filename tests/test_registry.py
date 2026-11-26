"""The failure registry: every entry is valid, in order, and re-runs to the verdicts it records.

``python scripts/run_registry.py`` does the same from the command line (and CI runs it as its own job).
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_registry", ROOT / "scripts" / "run_registry.py")
reg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reg)

ENTRIES = reg.load_entries()


def test_registry_has_the_first_two_failure_lab_entries():
    assert {"AFR-0001", "AFR-0002"} <= set(ENTRIES)
    assert ENTRIES["AFR-0001"]["links"]["lab"].startswith("examples/failure-lab/001-")
    assert ENTRIES["AFR-0002"]["links"]["lab"].startswith("examples/failure-lab/002-")


def test_ids_run_without_gaps_and_the_file_name_is_the_id():
    names = sorted(ENTRIES)
    assert names == [f"AFR-{i:04d}" for i in range(1, len(names) + 1)]
    assert all(e["id"] == n for n, e in ENTRIES.items())


@pytest.mark.parametrize("name", sorted(ENTRIES))
def test_entry_is_valid_against_the_schema_and_the_mapping(name):
    assert reg.validate(ENTRIES[name], name) == []


@pytest.mark.parametrize("name", sorted(ENTRIES))
def test_entry_reruns_to_its_recorded_verdicts(name):
    if ENTRIES[name]["status"] == "withdrawn":
        pytest.skip("withdrawn entries keep their ID and are not re-run")
    assert reg.judge(ENTRIES[name]) == []


def test_a_changed_verdict_is_caught():
    bad = copy.deepcopy(ENTRIES["AFR-0002"])
    bad["variants"]["original"]["expected_verdicts"]["T4-003"] = "pass"
    problems = reg.judge(bad)
    assert any("T4-003" in p and "expected pass" in p for p in problems)


@pytest.mark.parametrize("mutate, expect", [
    (lambda e: e["failing_checks"].append("T5-001"), "failing_checks"),
    (lambda e: e.update(category="AFC-10"), "category"),
    (lambda e: e.update(asi=["ASI05"]), "asi"),
    (lambda e: e["variants"]["original"].update(trace="examples/failure-lab/002-note-injection/traces/missing.otlp.jsonl"), "does not exist"),
    (lambda e: e.update(id="AFR-9999"), "does not match"),
    (lambda e: e.pop("credit"), "schema"),
])
def test_validation_rejects_a_broken_entry(mutate, expect):
    bad = copy.deepcopy(ENTRIES["AFR-0002"])
    mutate(bad)
    problems = reg.validate(bad, "AFR-0002")
    assert problems and any(expect in p for p in problems), problems


def test_the_index_is_up_to_date():
    assert reg.INDEX.read_text(encoding="utf-8") == reg.build_index(ENTRIES), "run python scripts/run_registry.py --write-index"


def test_entries_follow_the_wording_rules():
    for p in list((ROOT / "registry").rglob("*.json")) + [ROOT / "registry" / "README.md", reg.INDEX]:
        text = p.read_text(encoding="utf-8").lower()
        assert "synthetic" not in text, p
        assert not re.search(r"\bfork", text), p
        assert not re.search(r"precision|recall|p/r\b|world's first", text), p


def test_every_failure_lab_case_has_a_registry_entry():
    """A Failure Lab case lands together with its AFR entry (the case's README or reproduce.py is the entry's lab link)."""
    labs = {p.name for p in (ROOT / "examples" / "failure-lab").iterdir() if p.is_dir() and re.match(r"\d{3}-", p.name)}
    linked = {Path(e["links"]["lab"]).parent.name for e in ENTRIES.values() if e["links"].get("lab")}
    assert labs <= linked, f"Failure Lab cases without a registry entry: {sorted(labs - linked)}"


def test_schema_is_valid_json_schema():
    import jsonschema

    jsonschema.Draft202012Validator.check_schema(json.loads(reg.SCHEMA.read_text(encoding="utf-8")))
