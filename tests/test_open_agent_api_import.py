"""Keep the Open Agent API example and its negative control runnable."""

import json
from pathlib import Path

import pytest

from agentest.cli import main

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "open_agent_api_import"
TOOLS = EXAMPLE / "tools.json"


@pytest.mark.parametrize(
    ("source", "expected", "code"),
    [
        ("oaa-fixture.jsonl", {"T2-004": "pass", "T3-004": "pass", "X-016": "pass"}, 0),
        ("negative-control.jsonl", {"T2-004": "fail"}, 1),
    ],
)
def test_open_agent_api_import(source, expected, code, tmp_path):
    trace = tmp_path / "example.otlp.jsonl"
    report = tmp_path / "report.json"
    assert main([
        "std", "import", str(EXAMPLE / source), "--map", str(EXAMPLE / "mapping.json"),
        "--tools", str(TOOLS), "--service", "oaa-acp-fixture", "--out", str(trace),
    ]) == 0
    assert main([
        "std", "run", "--otlp", str(trace), "--tools", str(TOOLS), "--ids", ",".join(expected),
        "--mode", "strict", "--format", "json", "--out", str(report), "--strict",
    ]) == code
    assert {row["id"]: row["status"] for row in json.loads(report.read_text())["results"]} == expected
