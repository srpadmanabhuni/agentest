"""Local git-clone CLI: list/run/report/version, the mock agent (in-process and HTTP), and the clone shims."""

import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from agentest import local
from agentest.cli import main
from agentest.mock_agent import MockAgent, make_server

ROOT = Path(__file__).resolve().parents[1]


def test_packs_cover_all_ids():
    pk = local.packs()
    assert len(pk["all"]) == 130 and len(pk["extensions"]) == 20
    for name in ("security", "functional", "t1", "t7"):
        assert pk[name] and set(pk[name]) <= set(pk["all"])


def test_list_and_version(capsys):
    assert main(["list", "--packs"]) == 0
    assert "security" in capsys.readouterr().out
    assert main(["list", "--pack", "extensions"]) == 0
    assert "20 test(s)" in capsys.readouterr().out
    assert main(["list", "--pack", "nope"]) == 2
    assert main(["version"]) == 0


def test_run_mock_then_report(tmp_path, capsys):
    out = tmp_path / "r.json"
    assert main(["run", "--agent", "mock", "--pack", "security", "--out", str(out)]) == 0
    saved = json.loads(out.read_text())
    assert saved["pack"] == "security"
    ids = set(next(iter(saved["results"].values())))
    assert ids == set(local.packs()["security"])
    assert main(["report", "--format", "json", "--input", str(out)]) == 0
    capsys.readouterr()
    assert main(["report", "--format", "markdown", "--input", str(out)]) == 0
    assert "| ID |" in capsys.readouterr().out


def test_run_bad_inputs(tmp_path):
    assert main(["run", "--agent", "mock", "--pack", "nope", "--out", str(tmp_path / "x.json")]) == 2
    assert main(["run", "--agent", "ftp://x", "--out", str(tmp_path / "x.json")]) == 2
    assert main(["report", "--input", str(tmp_path / "missing.json")]) == 2


def test_http_mock_matches_in_process():
    srv = make_server("127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}"
        via_http = local.run(url, "all")["results"]
        in_proc = local.run("mock", "all")["results"]
        assert list(via_http.values()) == list(in_proc.values())
    finally:
        srv.shutdown()
    assert MockAgent().probes()


@pytest.mark.parametrize("cmd", [[sys.executable, "cli.py"], [sys.executable, "-m", "agentest"]])
def test_clone_entrypoints(cmd, tmp_path):
    env = {"PATH": "", "PYTHONPATH": ""}
    r = subprocess.run([*cmd, "--help"], cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 0 and "run" in r.stdout and "report" in r.stdout
    r = subprocess.run([*cmd, "version"], cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 0 and r.stdout.strip()
