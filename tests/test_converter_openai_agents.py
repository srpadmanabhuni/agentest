"""OpenAI Agents SDK converter: fixture items only, no SDK installed or imported."""

import sys

from agentest.standards import importers
from agentest.standards.converters import openai_agents as oa

MAP = {"dialect": "openai_agents", "observations": {"final_answer": ["output.final_answer"]}}


class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _new_items():
    triage, billing = Obj(name="fx_first"), Obj(name="fx_second")
    return [
        Obj(type="tool_call_item", agent=triage, raw_item=Obj(name="fx_lookup", arguments='{"id": 7}', call_id="c1")),
        Obj(type="tool_call_output_item", agent=triage, output="acct 7 ok", raw_item={"call_id": "c1", "output": "x"}),
        Obj(type="handoff_call_item", agent=triage, raw_item=Obj(name="fx_handoff_to_second")),
        Obj(type="handoff_output_item", agent=triage, source_agent=triage, target_agent=billing, raw_item={}),
        Obj(type="message_output_item", agent=billing, raw_item=Obj(content=[{"type": "output_text", "text": "Refunded."}])),
    ]


def test_new_items_objects():
    tr = oa.from_items(_new_items())
    assert [t["type"] for t in tr] == ["tool_call_item", "tool_call_output_item", "handoff_output_item",
                                       "message_output_item"]
    assert tr[0] == {"type": "tool_call_item", "tool": "fx_lookup", "args": {"id": 7}, "agent": "fx_first", "call_id": "c1"}
    assert tr[1]["output"] == "acct 7 ok" and tr[2] == {"type": "handoff_output_item", "agent": "fx_first", "to": "fx_second"}
    assert tr[3]["content"] == "Refunded."


def test_input_list_dicts():
    items = [{"role": "user", "content": "refund order 7"},
             {"type": "function_call", "name": "fx_refund", "arguments": "{\"order\": 7}", "call_id": "c9"},
             {"type": "function_call_output", "call_id": "c9", "output": "ok"},
             {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Done."}]}]
    rec = oa.to_record(oa.from_items(items, agent="fx_agent"), agent="fx_agent")
    assert rec["input"] == "refund order 7" and rec["output"]["final_answer"] == "Done."
    ep = importers.adapt(rec, MAP)
    assert [(c.name, c.arguments, c.result) for c in ep.tool_calls] == [("fx_refund", {"order": 7}, "ok")]


def test_record_imports_handoffs_and_final_output():
    rec = oa.to_record(oa.from_items(_new_items()), agent="fx_agent", input="refund 7", final_output={"ok": True})
    ep = importers.adapt(rec, MAP)
    assert [(h.source, h.target) for h in ep.handoffs] == [("fx_first", "fx_second")]
    assert ep.tool_calls[0].result == "acct 7 ok"
    assert rec["output"]["final_answer"] == '{"ok": true}'
    docs = importers.to_docs([rec], MAP, service="fx_agent")
    assert docs


def test_bad_arguments_kept_as_input():
    tr = oa.from_items([{"type": "function_call", "name": "fx", "arguments": "not json"}])
    assert tr[0]["args"] == {"input": "not json"}


def test_no_sdk_import():
    assert "agents" not in sys.modules
