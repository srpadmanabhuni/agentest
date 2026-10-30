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


# --- LangGraph state / checkpoint support ---
_MSGS = [{"type": "human", "content": "find 42", "id": "h1"},
         {"type": "ai", "content": "", "id": "a1", "tool_calls": [{"name": "fx_find", "args": {"item": 42}, "id": "c1"}]},
         {"type": "tool", "content": "found", "tool_call_id": "c1", "id": "t1"},
         {"type": "ai", "content": "Item 42 found.", "id": "a2"}]


def test_state_dict_snapshot_checkpoint_and_tuple_agree():
    class Snap:
        def __init__(self, values):
            self.values = values

    class Tup:
        def __init__(self, cp):
            self.checkpoint = cp
    want = lc.from_messages(_MSGS)
    assert lc.from_state({"messages": _MSGS}) == want
    assert lc.from_state(Snap({"messages": _MSGS})) == want
    assert lc.from_state({"channel_values": {"messages": _MSGS}}) == want
    assert lc.from_state(Tup({"channel_values": {"messages": _MSGS}})) == want


def test_state_dedupes_by_id_and_custom_key():
    assert lc.from_state({"chat": _MSGS + [_MSGS[3]]}, key="chat") == lc.from_messages(_MSGS)


def test_state_without_messages_fails_loudly():
    import pytest
    with pytest.raises(ValueError):
        lc.from_state({"other": 1})


def test_state_history_uses_newest_with_messages():
    hist = [{"values": {"messages": _MSGS}}, {"values": {"messages": _MSGS[:1]}}, {"values": {}}]
    assert lc.from_state_history(hist) == lc.from_messages(_MSGS)
    import pytest
    with pytest.raises(ValueError):
        lc.from_state_history([{"values": {}}])


def test_state_record_imports():
    rec = lc.to_record(lc.from_state({"messages": _MSGS}), agent="fx_agent")
    ep = importers.adapt(rec, MAP)
    assert [c.name for c in ep.tool_calls] == ["fx_find"] and ep.tool_calls[0].result == "found"
    assert rec["output"]["final_answer"] == "Item 42 found."
