import json

import pytest

from agentest.cli import main


def results(ids, capsys):
    args = ["std", "run", "--agent", "eager", "--format", "json"]
    if ids is not None:
        args.extend(["--ids", ids])
    assert main(args) == 0
    return json.loads(capsys.readouterr().out)["results"]


@pytest.mark.parametrize("class_id", ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "X"])
def test_class_selects_all_matching_results_without_changing_verdicts(class_id, capsys):
    expected = [r for r in results(None, capsys) if r["id"].startswith(class_id + "-")]
    assert expected
    assert results(class_id, capsys) == expected


def test_mixed_classes_and_exact_ids_preserve_order_and_remove_duplicates(capsys):
    expected = [r for r in results(None, capsys) if r["id"].startswith("T5-") or r["id"] == "T6-002"]
    assert results(" T5, T6-002, T5-001, T5, ", capsys) == expected


def test_exact_id_still_selects_only_that_result(capsys):
    expected = [r for r in results(None, capsys) if r["id"] == "T5-001"]
    assert results("T5-001", capsys) == expected


@pytest.mark.parametrize("ids, unknown", [("T9-999", "T9-999"), ("T5,T9", "T9"), ("T5-*", "T5-*")])
def test_unknown_ids_still_exit_two(ids, unknown, capsys):
    assert main(["std", "run", "--agent", "eager", "--ids", ids]) == 2
    assert capsys.readouterr().out.strip() == f"unknown test IDs: {unknown}"
