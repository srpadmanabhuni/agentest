"""Bring-your-own-agent path: Recorder -> episodes JSONL -> `agentest check`."""

import json
import subprocess
import sys
from pathlib import Path

from agentest import byo
from agentest.cli import main

EX = Path(__file__).resolve().parents[1] / "examples" / "byo_agent" / "my_agent.py"


def _make(tmp_path, buggy=False):
    out = tmp_path / ("bug.jsonl" if buggy else "ok.jsonl")
    args = [sys.executable, str(EX), str(out)] + (["--buggy"] if buggy else [])
    subprocess.run(args, check=True, capture_output=True)
    return out


def test_good_agent_all_pass(tmp_path):
    res = byo.run(byo.load(_make(tmp_path)))
    assert {r.status for r in res.values()} == {"pass"}, {i: r for i, r in res.items() if r.status != "pass"}


def test_buggy_agent_caught(tmp_path):
    res = byo.run(byo.load(_make(tmp_path, buggy=True)))
    for i in ("T1-001", "T1-003", "T1-018", "T2-003"):
        assert res[i].status == "fail", i


def test_cli_reports_and_strict(tmp_path):
    p = _make(tmp_path, buggy=True)
    md, html = tmp_path / "r.md", tmp_path / "r.html"
    assert main(["check", str(p), "--md", str(md), "--html", str(html)]) == 0
    assert main(["check", str(p), "--strict"]) == 1
    assert "FAIL" in md.read_text() and "<table>" in html.read_text()


def test_bad_inputs(tmp_path):
    assert main(["check", str(tmp_path / "missing.jsonl")]) == 2
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not json\n")
    assert main(["check", str(bad)]) == 2
    empty = tmp_path / "e.jsonl"
    empty.write_text("\n")
    assert main(["check", str(empty)]) == 2
    arr = tmp_path / "a.jsonl"
    arr.write_text("[1,2]\n")
    assert main(["check", str(arr)]) == 2


def test_no_oracle_is_na(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text(json.dumps({"output": {"a": 1}, "trace": [{"kind": "tool", "name": "t", "mono": 0.1, "data": {"args": {}, "reason": "a sufficiently long reason"}}]}) + "\n")
    res = byo.run(byo.load(p))
    assert res["T1-001"].status == "n/a" and res["X-003"].status == "pass"


def test_malformed_trace_is_error_not_crash(tmp_path):
    p = tmp_path / "m.jsonl"
    p.write_text(json.dumps({"output": {}, "trace": [{"kind": "tool", "mono": "soon"}]}) + "\n")
    res = byo.run(byo.load(p))
    assert res["X-007"].status == "fail" and "ValueError" in res["X-007"].detail  # v2: malformed evidence is a reported fail, never a crash


def test_version_cmd(capsys):
    from agentest import __version__

    assert main(["version"]) == 0 and capsys.readouterr().out.strip() == __version__
