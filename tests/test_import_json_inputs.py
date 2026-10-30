"""`agentest std import` input files: .jsonl, a .json array or single object, a bare message list; clear errors."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agentest.standards import importers
from agentest.standards.converters import langchain as lc

REC = {"agent": "fx_agent", "probe": "p", "rep": 0, "input": "hi",
       "trace": [{"role": "human", "content": "hi"}, {"role": "ai", "content": "hello"}],
       "output": {"final_answer": "hello"}}
MSGS = [{"type": "system", "content": "sys"}, {"type": "human", "content": "Look up item 7."},
        {"type": "ai", "content": "I will check the inventory for item 7.",
         "tool_calls": [{"name": "fx_find", "args": {"item": 7}, "id": "c1"}]},
        {"type": "tool", "content": "{\"stock\": 3}", "tool_call_id": "c1"}, {"type": "ai", "content": "In stock."}]
ENV = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
MAP = {"dialect": "langgraph_msgs", "observations": {"final_answer": ["output.final_answer"]}}


def test_jsonl_array_object(tmp_path):
    (tmp_path / "a.jsonl").write_text(json.dumps(REC) + "\n\n" + json.dumps(REC) + "\n")
    (tmp_path / "b.json").write_text(json.dumps([REC, REC]))
    (tmp_path / "c.json").write_text(json.dumps(REC))
    assert [len(importers.read_native(tmp_path / n)) for n in ("a.jsonl", "b.json", "c.json")] == [2, 2, 1]


def test_bare_message_list_is_one_record(tmp_path):
    (tmp_path / "run.json").write_text(json.dumps(MSGS))
    (r,) = importers.read_native(tmp_path / "run.json")
    assert r["agent"] == "run" and r["input"] == "Look up item 7." and r["output"]["final_answer"] == "In stock."


@pytest.mark.parametrize("body", ["42", '"x"', "[1, 2]", "{not json"])
def test_clear_errors(tmp_path, body):
    (tmp_path / "bad.json").write_text(body)
    with pytest.raises(ValueError, match="bad.json"):
        importers.read_native(tmp_path / "bad.json")


def test_ai_text_becomes_tool_reason():
    rec = lc.to_record(lc.from_messages(MSGS), agent="fx_agent")
    assert rec["trace"][1]["tool_calls"][0]["reason"] == "I will check the inventory for item 7."
    (doc,) = importers.to_docs([rec], MAP, service="fx_agent")
    spans = doc["resourceSpans"][0]["scopeSpans"][0]["spans"]
    tool = [s for s in spans if s["name"].startswith("execute_tool")]
    assert tool and {"key": "agentest.tool.reason", "value": {"stringValue": "I will check the inventory for item 7."}} in tool[0]["attributes"]


def test_no_text_no_invented_reason():
    tr = lc.from_messages([{"type": "ai", "content": "", "tool_calls": [{"name": "fx_find", "args": {}}]}])
    assert "reason" not in tr[0]["tool_calls"][0]


def test_cli_imports_json_and_reports_errors(tmp_path):
    (tmp_path / "run.json").write_text(json.dumps(MSGS))
    (tmp_path / "map.json").write_text(json.dumps(MAP))
    out = tmp_path / "o.otlp.jsonl"
    cmd = [sys.executable, "-m", "agentest.cli", "std", "import", str(tmp_path / "run.json"), "--map", str(tmp_path / "map.json"), "--out", str(out)]
    assert subprocess.run(cmd, capture_output=True, text=True, env=ENV).returncode == 0 and len(out.read_text().splitlines()) == 1
    (tmp_path / "bad.json").write_text("42")
    p = subprocess.run(cmd[:5] + [str(tmp_path / "bad.json")] + cmd[6:], capture_output=True, text=True, env=ENV)
    assert p.returncode == 2 and "expected a JSON object" in (p.stdout + p.stderr)
