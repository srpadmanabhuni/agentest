"""LangChain / LangGraph converter: fixture traces only, no framework installed or imported."""

import json
import sys
from pathlib import Path

from agentest.standards import importers
from agentest.standards.converters import langchain as lc

FX = Path(__file__).parent / "fixtures_adapters"
MAP = {"dialect": "langgraph_msgs", "observations": {"final_answer": ["output.final_answer"]}}


def _load(name):
    return json.loads((FX / name).read_text())


def test_messages_all_shapes():
    tr = lc.from_messages(_load("langchain_messages.json"))
    assert [t["role"] for t in tr] == ["human", "ai", "tool", "ai", "tool", "ai"]
    assert tr[1]["tool_calls"][0] == {"name": "fx_find", "args": {"item": 42}, "id": "c1"}
    assert tr[3]["tool_calls"][0]["name"] == "fx_reserve" and tr[3]["tool_calls"][0]["args"] == {"item": 42}
    assert tr[2]["tool_call_id"] == "c1"


def test_duck_typed_objects():
    class M:
        def __init__(self, type, content, tool_calls=None):
            self.type, self.content, self.tool_calls = type, content, tool_calls or []
    tr = lc.from_messages([M("human", "hi"), M("ai", "", [{"name": "fx_find", "args": {}, "id": "a"}]), M("ai", "done")])
    assert tr[1]["tool_calls"][0]["name"] == "fx_find" and tr[-1]["content"] == "done"


def test_stream_events_ignore_chunks_and_dedupe_tool_start():
    tr = lc.from_stream_events(_load("langgraph_stream_events.json"))
    assert [t["role"] for t in tr] == ["human", "ai", "tool", "ai"]
    assert tr[2]["content"] == '{"stock": 3}'


def test_record_imports_to_otel_spans():
    rec = lc.to_record(lc.from_messages(_load("langchain_messages.json")), agent="fx_agent")
    assert rec["input"] == "Find item 42 and reserve it." and rec["output"]["final_answer"] == "Item 42 is reserved."
    ep = importers.adapt(rec, MAP)
    assert [c.name for c in ep.tool_calls] == ["fx_find", "fx_reserve"]
    assert ep.tool_calls[0].result is not None
    docs = importers.to_docs([rec], MAP, service="fx_agent")
    assert docs and "resourceSpans" in json.dumps(docs[0])


def test_no_framework_import():
    assert not any(m.startswith(("langchain", "langgraph")) for m in sys.modules)
