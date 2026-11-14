import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentest.cli import main


def test_list_all(capsys):
    assert main(["list"]) == 0
    assert "110 test(s)" in capsys.readouterr().out


def test_list_class_t3(capsys):
    assert main(["list", "--class", "T3", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 14 and all(r["class_id"] == "T3" for r in rows)


def test_list_bad_class():
    assert main(["list", "--class", "T9"]) == 2


def test_framework_mapping_covers_all_classes():
    text = (Path(__file__).resolve().parents[2] / "docs" / "FRAMEWORK-MAPPING.md").read_text(
        encoding="utf-8"
    )
    for c in ("T1", "T2", "T3", "T4", "T5", "T6", "T7"):
        assert f"| {c} " in text


# --- severity / eval-group filters -------------------------------------------


def _rows(args, capsys):
    assert main(args) == 0
    return json.loads(capsys.readouterr().out)


def test_list_severity_single(capsys):
    rows = _rows(["list", "--severity", "critical", "--json"], capsys)
    assert rows and all(r["severity"] == "critical" for r in rows)


def test_list_severity_multiple_is_a_union(capsys):
    crit = _rows(["list", "--severity", "critical", "--json"], capsys)
    high = _rows(["list", "--severity", "high", "--json"], capsys)
    both = _rows(["list", "--severity", "critical,high", "--json"], capsys)
    assert len(both) == len(crit) + len(high)
    assert {r["id"] for r in both} == {r["id"] for r in crit} | {r["id"] for r in high}


def test_list_severity_is_case_insensitive(capsys):
    lower = _rows(["list", "--severity", "critical", "--json"], capsys)
    upper = _rows(["list", "--severity", "CRITICAL", "--json"], capsys)
    assert [r["id"] for r in lower] == [r["id"] for r in upper]


def test_list_severity_tolerates_spaces_and_empty_items(capsys):
    spaced = _rows(["list", "--severity", "critical, high", "--json"], capsys)
    plain = _rows(["list", "--severity", "critical,high", "--json"], capsys)
    assert [r["id"] for r in spaced] == [r["id"] for r in plain]


def test_list_unknown_severity_exits_2_and_lists_valid_values(capsys):
    assert main(["list", "--severity", "bogus"]) == 2
    err = capsys.readouterr().err
    assert "bogus" in err
    # the message must name the values that would have worked
    for valid in ("critical", "high", "medium", "low"):
        assert valid in err


def test_list_group_single(capsys):
    rows = _rows(["list", "--group", "security", "--json"], capsys)
    assert rows and all(r["eval_group"] == "security" for r in rows)


def test_list_group_multiple(capsys):
    rows = _rows(["list", "--group", "privacy,bias_fairness", "--json"], capsys)
    assert rows
    assert {r["eval_group"] for r in rows} == {"privacy", "bias_fairness"}


def test_list_unknown_group_exits_2(capsys):
    assert main(["list", "--group", "nope"]) == 2
    assert "nope" in capsys.readouterr().err


def test_list_severity_and_group_combine_as_and(capsys):
    rows = _rows(["list", "--severity", "critical", "--group", "security", "--json"], capsys)
    assert all(r["severity"] == "critical" and r["eval_group"] == "security" for r in rows)


def test_list_filters_combine_with_class(capsys):
    rows = _rows(["list", "--class", "T3", "--severity", "high", "--json"], capsys)
    assert all(r["class_id"] == "T3" and r["severity"] == "high" for r in rows)


def test_list_json_includes_eval_group(capsys):
    rows = _rows(["list", "--json"], capsys)
    assert all("eval_group" in r for r in rows)


def test_list_no_filter_is_unchanged(capsys):
    """Adding filters must not alter the default output."""
    rows = _rows(["list", "--json"], capsys)
    assert len(rows) == 110


def test_list_text_output_counts_filtered_rows(capsys):
    assert main(["list", "--severity", "low"]) == 0
    out = capsys.readouterr().out
    assert "1 test(s)" in out


# --- module entry point ------------------------------------------------------


def test_module_entry_point_works():
    """`python -m agentest.cli list` must work, not just `from agentest.cli import main`.

    The `if __name__ == "__main__"` guard used to sit above `_cmd_list`, so the
    module form raised NameError while the import form passed. Every test above
    uses the import form and therefore could not see it.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "agentest.cli", "list", "--severity", "low"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "test(s)" in proc.stdout
    assert "NameError" not in proc.stderr


@pytest.mark.parametrize("sub", [["list"], ["version"]])
def test_module_entry_point_handles_multiple_subcommands(sub):
    proc = subprocess.run(
        [sys.executable, "-m", "agentest.cli", *sub],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "NameError" not in proc.stderr
