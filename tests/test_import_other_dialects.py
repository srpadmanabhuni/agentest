"""Connector group: the other built-in dialects, imported in the trace format 1.0.0.

- ``steps``: plain Python steps, LangGraph node logs, LlamaIndex retrieval steps and CrewAI task outputs.
- ``events``, ``autogen`` and ``smolagents`` (the bundled smolagents example as well).

Every import validates against the schema, keeps every span, reads back as the same runs and gets the same verdicts
on all default checks."""

from __future__ import annotations

import json

import pytest

from agentest.standards import metadata
from agentest.standards.importers import is_write_from_tools, read_native
from tests.connector_agent import OBS, agent, is_write, record
from tests.connector_roundtrip import ROOT, check, resource

OK = {"executed": [{"order_id": "ORD-7", "amount": 40}], "approvals": [{"action": "request_refund", "granted": True}]}
NATIVE = {"run_id": "run-42", "user_id": "user-3", "started_at": "2026-11-18T01:17:00+05:30"}

STEPS = [  # CrewAI task outputs, a LangGraph durable node log and a retrieval step
    {"agent": "triage", "output": "Order ORD-7 is eligible."},
    {"node": "billing", "log": [{"node": "lookup_order", "order_id": "ORD-7"}, {"node": "request_refund", "order_id": "ORD-7", "amount": 40}]},
    {"step": "policy_search", "sources": [{"id": "refund-policy", "text": "Refunds up to the order total."}]},
    {"agent": "billing", "output": "Your refund for ORD-7 was issued."},
]
EVENTS = [
    {"kind": "message", "name": "TextMessage", "data": {"source": "user", "content": "Refund order ORD-7"}},
    {"kind": "route", "name": "triage", "data": {"next": "billing"}},
    {"kind": "tool", "name": "lookup_order", "data": {"args": {"order_id": "ORD-7"}, "result": {"total": 40}}},
    {"kind": "write", "name": "request_refund", "data": {"order_id": "ORD-7", "amount": 40}},
    {"kind": "tool", "name": "lookup_order", "data": {"args": {"order_id": "ORD-3"}, "error": "order service unavailable"}},
    {"kind": "message", "name": "TextMessage", "data": {"source": "billing", "content": "Your refund for ORD-7 was issued."}},
]
AUTOGEN = [
    {"type": "TextMessage", "source": "user", "content": "Refund order ORD-7"},
    {"type": "ToolCallRequestEvent", "source": "billing",
     "content": "[FunctionCall(id='c1', arguments='{\"order_id\": \"ORD-7\"}', name='lookup_order'), "
                "FunctionCall(id='c2', arguments='{\"order_id\": \"ORD-7\", \"amount\": 40}', name='request_refund')]"},
    {"type": "TextMessage", "source": "billing", "content": "Your refund for ORD-7 was issued."},
]
SMOL = [
    {"task": "Refund order ORD-7"},
    {"step_number": 1, "observations": '{"total": 40}',
     "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "lookup_order", "arguments": '{"order_id": "ORD-7"}'}}]},
    {"step_number": 2, "observations": '{"status": "issued"}',
     "tool_calls": [{"id": "c2", "type": "function", "function": {"name": "request_refund", "arguments": {"order_id": "ORD-7", "amount": 40}}}]},
    {"output": "Your refund for ORD-7 was issued."},
]
CASES = {"steps": STEPS, "events": EVENTS, "autogen": AUTOGEN, "smolagents": SMOL}


def _records(trace: list) -> list[dict]:
    recs = [record("refund-ok", rep, "Refund order ORD-7", trace, "Your refund for ORD-7 was issued.", **OK, **NATIVE) for rep in range(3)]
    recs.append(record("refund-repeat", 0, "Refund order ORD-7", trace + trace, "Refund sent.", executed=OK["executed"] * 2))
    recs.append(record("empty", 0, "", [], ""))
    return recs


@pytest.mark.parametrize("dialect", sorted(CASES))
def test_trace_format_import_keeps_verdicts(tmp_path, dialect):
    mapping = {"dialect": dialect, "framework": f"{dialect} (use-case records)", "observations": OBS}
    docs, verdicts = check(_records(CASES[dialect]), mapping, "refund_desk", agent(tmp_path), is_write)
    assert any(v != "n/a" for v in verdicts.values())
    r = resource(docs[0])
    assert (r["agentest.run.id"], r["user.id"]) == ("run-42", "user-3") and int(r["agentest.source.start_time_unix_nano"]) == 1794944820000000000


def test_bundled_smolagents_example():
    sm, lg = ROOT / "examples" / "smolagents_import", ROOT / "examples" / "langgraph_import" / "agents" / "expense_bot"
    mapping = json.loads((sm / "import" / "map.json").read_text(encoding="utf-8"))
    check(read_native(sm / "native" / "expense_bot.jsonl"), mapping, "expense_bot", metadata.load(lg), is_write_from_tools(lg / "tools.json"))


def test_file_mapping_function(tmp_path):
    (tmp_path / "my_dialect.py").write_text(
        "from agentest.standards.episode import ToolCall\n\n"
        "def to_trace(raw, ep):\n"
        "    for t in raw['trace']:\n"
        "        ep.tool_calls.append(ToolCall(name=t['call'], arguments=t.get('args', {}), result=t.get('result')))\n", encoding="utf-8")
    trace = [{"call": "lookup_order", "args": {"order_id": "ORD-7"}, "result": {"total": 40}},
             {"call": "request_refund", "args": {"order_id": "ORD-7", "amount": 40}, "result": {"status": "issued"}}]
    mapping = {"dialect": "file:my_dialect.py", "framework": "own adapter", "observations": OBS}
    from agentest.standards.importers import to_docs

    before = to_docs(_records(trace), dict(mapping), "refund_desk", is_write, base=tmp_path)
    after = to_docs(_records(trace), {**mapping, "trace_format": "1.0.0"}, "refund_desk", is_write, base=tmp_path)
    assert [d["resourceSpans"][0]["scopeSpans"] for d in after] == [d["resourceSpans"][0]["scopeSpans"] for d in before]
    assert all(resource(d)["agentest.trace_format.version"] == "1.0.0" for d in after)
