"""Opt-in responsible-AI additions on `std run --ids` and `list --opt-in`.

Default `std run` and default `list` output must stay byte-identical to main
(9e756a2) snapshots captured before this change. No rule, scorer or verdict change.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentest.cli import main
from agentest.standards.catalog import RAI_ADDITION_IDS

GOLDEN = Path(__file__).resolve().parent / "golden"
FIVE = ("T1-020", "T1-021", "T3-018", "T3-019", "T7-017")


def test_registry_api_and_roadmap_agree_on_the_five_ids():
    roadmap = (Path(__file__).resolve().parents[2] / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    assert set(RAI_ADDITION_IDS) == set(FIVE)
    assert tuple(RAI_ADDITION_IDS) == FIVE
    for tid in FIVE:
        assert tid in roadmap


@pytest.mark.parametrize("tid", FIVE)
def test_std_run_ids_accepts_each_rai_addition(tid, capsys):
    assert main(["std", "run", "--agent", "eager", "--ids", tid, "--format", "json"]) == 0
    rows = json.loads(capsys.readouterr().out)["results"]
    assert [r["id"] for r in rows] == [tid]
    assert {r["status"] for r in rows} <= {"pass", "fail", "n/a"}


def test_std_run_ids_accepts_all_five_together(capsys):
    assert main(["std", "run", "--agent", "eager", "--ids", ",".join(FIVE), "--format", "json"]) == 0
    rows = json.loads(capsys.readouterr().out)["results"]
    assert [r["id"] for r in rows] == list(FIVE)
    assert {r["status"] for r in rows} <= {"pass", "fail", "n/a"}


def test_std_run_ids_mixes_opt_in_with_a_default_id_without_changing_its_verdict(capsys):
    assert main(["std", "run", "--agent", "eager", "--ids", "T1-018", "--format", "json"]) == 0
    baseline = json.loads(capsys.readouterr().out)["results"]
    assert main(["std", "run", "--agent", "eager", "--ids", "T1-018,T1-020", "--format", "json"]) == 0
    mixed = json.loads(capsys.readouterr().out)["results"]
    assert [r["id"] for r in mixed] == ["T1-018", "T1-020"]
    assert mixed[0] == baseline[0]


def test_list_opt_in_marks_the_five_and_not_the_default(capsys):
    assert main(["list", "--opt-in"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[-1] == "5 opt-in test(s)"
    body = lines[:-1]
    assert [line.split()[0] for line in body] == list(FIVE)
    assert all("[opt-in]" in line for line in body)


def test_list_opt_in_json_marks_opt_in(capsys):
    assert main(["list", "--opt-in", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [r["id"] for r in rows] == list(FIVE)
    assert all(r.get("opt_in") is True for r in rows)


def test_default_list_output_matches_main_snapshot(capsys):
    assert main(["list"]) == 0
    captured = capsys.readouterr()
    assert captured.out == (GOLDEN / "list-default.stdout").read_text(encoding="utf-8")
    assert captured.err == ""


def test_default_std_run_output_matches_main_snapshot(capsys):
    assert main(["std", "run"]) == 0
    captured = capsys.readouterr()
    assert captured.out == (GOLDEN / "std-run-default.stdout").read_text(encoding="utf-8")
    assert captured.err == ""
