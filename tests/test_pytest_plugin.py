"""The pytest plugin (entry point pytest11) gives the same verdicts as `agentest std run`."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentest.pytest_plugin import AgentestReport, run_agentest

ROOT = Path(__file__).resolve().parents[1]
A01 = ROOT / "agents" / "a01"
OTLP = A01 / "traces" / "a01.otlp.jsonl"
CARD = A01 / "agent-card.json"
TOOLS = A01 / "tools.json"


@pytest.fixture(scope="module")
def cli_cells(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict]:
    out = tmp_path_factory.mktemp("cli") / "r.json"
    subprocess.run(
        [sys.executable, "-m", "agentest", "std", "run", "--otlp", str(OTLP), "--card", str(CARD), "--tools", str(TOOLS), "--json", str(out)],
        check=True,
        capture_output=True,
    )
    return next(iter(json.loads(out.read_text(encoding="utf-8")).values()))


def test_fixture_matches_cli(agentest_check, cli_cells) -> None:
    report = agentest_check(OTLP, card=CARD, tools=TOOLS)
    assert {t: c["status"] for t, c in report.cells.items()} == {t: c["status"] for t, c in cli_cells.items()}


def test_assert_helpers_follow_statuses(agentest_check, cli_cells) -> None:
    report = agentest_check(OTLP, card=CARD, tools=TOOLS)
    passing = report.ids("pass")
    assert passing, "the example agent should pass at least one check"
    report.assert_pass(*passing[:3])
    report.assert_no_fail(ignore=report.ids("fail"))
    for status in ("fail", "n/a"):
        others = report.ids(status)
        if others:
            with pytest.raises(AssertionError, match=others[0]):
                report.assert_pass(others[0])
    if report.ids("fail"):
        with pytest.raises(AssertionError):
            report.assert_no_fail()


def test_ids_limit_the_report(agentest_check, cli_cells) -> None:
    some = sorted(cli_cells)[:2]
    report = agentest_check(OTLP, card=CARD, tools=TOOLS, ids=some)
    assert sorted(report.cells) == some


def test_unknown_id_and_missing_file(tmp_path: Path) -> None:
    report = AgentestReport("x", {"T1-001": {"status": "pass", "detail": ""}})
    with pytest.raises(AssertionError, match="T9-999"):
        report.assert_pass("T9-999")
    with pytest.raises(KeyError):
        report.status("T9-999")
    with pytest.raises(FileNotFoundError):
        run_agentest(tmp_path / "missing.otlp.jsonl", workdir=tmp_path)
