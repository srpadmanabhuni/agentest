"""``agentest std diff`` compares two saved ``std run --json`` verdict files.

Transitions are grouped by task (the agent id in the file) and check ID.
``--fail-on-new-fail`` exits 1 only when a check's status becomes fail.
"""
from __future__ import annotations

import json
from pathlib import Path

from agentest.cli import main
from agentest.standards.verdict_diff import diff_verdicts, load_verdicts, render_diff


def _write(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc), encoding="utf-8")


def _pair(tmp_path: Path):
    old = {
        "eager": {
            "T1-001": {"status": "pass", "detail": "ok"},
            "T1-003": {"status": "fail", "detail": "rate"},
            "T1-018": {"status": "pass", "detail": "ok"},
            "X-001": {"status": "n/a", "detail": "no signal"},
            "T2-001": {"status": "fail", "detail": "order"},
        },
        "quiet": {"T1-001": {"status": "pass", "detail": "ok"}},
    }
    new = {
        "eager": {
            "T1-001": {"status": "fail", "detail": "now fails"},
            "T1-003": {"status": "pass", "detail": "recovered"},
            "T1-018": {"status": "n/a", "detail": "signal gone"},
            "X-001": {"status": "fail", "detail": "appeared"},
            "T2-001": {"status": "n/a", "detail": "no longer judged"},
        },
        "quiet": {"T1-001": {"status": "pass", "detail": "still ok"}},
    }
    _write(tmp_path / "old.json", old)
    _write(tmp_path / "new.json", new)
    return tmp_path / "old.json", tmp_path / "new.json"


def test_transitions_grouped_by_task_and_check(tmp_path):
    old_p, new_p = _pair(tmp_path)
    report = diff_verdicts(load_verdicts(old_p), load_verdicts(new_p))
    assert report["newly_failing"] == [
        {"task": "eager", "id": "T1-001", "before": "pass", "after": "fail"},
        {"task": "eager", "id": "X-001", "before": "n/a", "after": "fail"},
    ]
    assert report["newly_passing"] == [
        {"task": "eager", "id": "T1-003", "before": "fail", "after": "pass"},
    ]
    by_id = {(c["task"], c["id"]): (c["before"], c["after"]) for c in report["transitions"]}
    assert by_id[("eager", "T1-018")] == ("pass", "n/a")
    assert by_id[("eager", "T2-001")] == ("fail", "n/a")
    assert ("quiet", "T1-001") not in by_id  # unchanged status is not a transition
    text = render_diff(report)
    assert text.splitlines()[:2] == ["newly failing: 2", "newly passing: 1"]
    assert "eager\n  T1-001  pass -> fail\n  T1-003  fail -> pass\n  T1-018  pass -> n/a\n  T2-001  fail -> n/a\n  X-001  n/a -> fail" in text
    assert "quiet" not in text


def test_versioned_report_and_missing_check(tmp_path):
    old = {"schema": "agentest.verdicts/1", "results": [{"agent": "desk", "id": "T1-001", "status": "pass", "detail": "ok"}]}
    new = {"results": [{"agent": "desk", "id": "T1-002", "status": "fail", "detail": "added"}]}
    _write(tmp_path / "old.json", old)
    _write(tmp_path / "new.json", new)
    report = diff_verdicts(load_verdicts(tmp_path / "old.json"), load_verdicts(tmp_path / "new.json"))
    assert {(c["id"], c["before"], c["after"]) for c in report["transitions"]} == {
        ("T1-001", "pass", "missing"),
        ("T1-002", "missing", "fail"),
    }
    assert report["newly_failing"] == [{"task": "desk", "id": "T1-002", "before": "missing", "after": "fail"}]
    assert report["newly_passing"] == []


def test_cli_fail_on_new_fail_exit_code(tmp_path, capsys):
    old_p, new_p = _pair(tmp_path)
    out = tmp_path / "diff.json"
    assert main(["std", "diff", str(old_p), str(new_p), "--fail-on-new-fail", "--json", str(out)]) == 1
    text = capsys.readouterr().out
    assert "newly failing: 2" in text
    assert "T1-018  pass -> n/a" in text
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert len(saved["newly_failing"]) == 2
    assert len(saved["newly_passing"]) == 1
    assert saved["transitions"]


def test_cli_exit_zero_when_nothing_newly_fails(tmp_path, capsys):
    old = {"eager": {"T1-001": {"status": "fail", "detail": "x"}, "T1-018": {"status": "pass", "detail": "ok"}}}
    new = {"eager": {"T1-001": {"status": "pass", "detail": "y"}, "T1-018": {"status": "n/a", "detail": "z"}}}
    _write(tmp_path / "old.json", old)
    _write(tmp_path / "new.json", new)
    assert main(["std", "diff", str(tmp_path / "old.json"), str(tmp_path / "new.json"), "--fail-on-new-fail"]) == 0
    text = capsys.readouterr().out
    assert "newly failing: 0" in text
    assert "newly passing: 1" in text
    assert "T1-018  pass -> n/a" in text
    # without the flag, a new fail is still reported and the process exits 0
    new["eager"]["T1-001"]["status"] = "fail"
    old["eager"]["T1-001"]["status"] = "pass"
    _write(tmp_path / "old.json", old)
    _write(tmp_path / "new.json", new)
    assert main(["std", "diff", str(tmp_path / "old.json"), str(tmp_path / "new.json")]) == 0
    assert "newly failing: 1" in capsys.readouterr().out


def test_cli_rejects_a_bad_file(tmp_path, capsys):
    good = tmp_path / "old.json"
    _write(good, {"eager": {"T1-001": {"status": "pass", "detail": "ok"}}})
    bad = tmp_path / "new.json"
    bad.write_text("{", encoding="utf-8")
    assert main(["std", "diff", str(good), str(bad)]) == 2
    assert "not valid JSON" in capsys.readouterr().out
    assert main(["std", "diff", str(good)]) == 2
    assert "OLD.json NEW.json" in capsys.readouterr().out
