"""Trace format reader support: D2 read aliases and D7 per-tool declarations, each shown to be read."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from agentest.standards.episode import Episode
from agentest.standards.metadata import DECLARABLE_ON_TOOL, Agent
from agentest.standards.otel import READ_ALIASES, _attrs, aliased, apply_tool_declarations, from_otlp, to_otlp
from agentest.standards.rules import evaluate

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "src/agentest/standards/schemas/trace-format.schema.json").read_text(encoding="utf-8"))
SEMCONV = yaml.safe_load((ROOT / "src/agentest/standards/semconv.yaml").read_text(encoding="utf-8"))


def _doc(root_extra: dict | None = None, tool_extra: dict | None = None, approval: dict | None = None) -> dict:
    ep = Episode("desk", "case-1", 0, input="Refund order ORD-7", final_answer="Done.")
    ep.add_tool("lookup_order", {"order_id": "ORD-7"}, {"total": 40})
    ep.add_tool("reset_password", {"user": "u1"}, {"ok": True})
    doc = to_otlp(ep, "desk", root_extra or {}, [tool_extra or {}, {}])
    spans = doc["resourceSpans"][0]["scopeSpans"][0]["spans"]
    if approval is not None:
        spans.append({"traceId": spans[0]["traceId"], "spanId": "ab" * 8, "parentSpanId": spans[0]["spanId"], "name": "agentest.approval",
                      "kind": 1, "startTimeUnixNano": spans[-1]["endTimeUnixNano"], "endTimeUnixNano": str(int(spans[-1]["endTimeUnixNano"]) + 1),
                      "attributes": _attrs({"agentest.approval.action": "share_record", "agentest.approval.granted": True, **approval})})
    return json.loads(json.dumps(doc))


def test_aliases_match_the_schema_registry():
    semconv_old = {k for st in SEMCONV["styles"].values() for k in (st.get("rename") or {})} | {
        k for st in SEMCONV["styles"].values() for k in (st.get("json_messages") or {})}
    schema = [(alias, name) for name, d in SCHEMA["x-agentest-attributes"].items() for alias in d.get("aliases") or []]
    assert {(a, n) for a, n in schema if a not in semconv_old} == set(READ_ALIASES.items())
    assert all(a in semconv_old for a, n in schema if (a, n) not in READ_ALIASES.items())


def test_approval_data_class_alias_and_canonical():
    assert from_otlp(_doc(approval={"agentest.approval.dataClass": "health"})).approvals[0]["dataClass"] == "health"
    assert from_otlp(_doc(approval={"agentest.approval.data_class": "health"})).approvals[0]["dataClass"] == "health"
    both = {"agentest.approval.data_class": "health", "agentest.approval.dataClass": "contact"}
    assert from_otlp(_doc(approval=both)).approvals[0]["dataClass"] == "health"


def test_output_alias_on_root_and_tool_spans():
    r = from_otlp(_doc({"agentest.output": '{"status": "ok"}'}, {"agentest.output": '{"rows": 1}'}))
    assert r.attrs["agentest.output.structured"] == '{"status": "ok"}' and r.tools[0].attrs["agentest.output.structured"] == '{"rows": 1}'
    r = from_otlp(_doc({"agentest.output": "old", "agentest.output.structured": "new"}))
    assert r.attrs["agentest.output.structured"] == "new" and r.attrs["agentest.output"] == "old"


def test_role_and_initial_state_aliases():
    assert json.loads(from_otlp(_doc({"enduser.roles": ["admin"]})).attrs["user.roles"]) == ["admin"]
    assert from_otlp(_doc({"agentest.auth.role": "viewer"})).attrs["user.roles"] == "viewer"
    assert from_otlp(_doc({"enduser.roles": ["a"], "agentest.auth.role": "b"})).attrs["user.roles"] == '["a"]'
    assert from_otlp(_doc({"user.roles": ["c"], "agentest.auth.role": "b"})).attrs["user.roles"] == '["c"]'
    assert from_otlp(_doc({"agentest.undo.before": '{"k": 1}'})).attrs["agentest.task.initial_state"] == '{"k": 1}'


def test_alias_copies_do_not_change_span_blobs():
    plain = from_otlp(_doc({"agentest.output": "x" * 400, "enduser.roles": ["admin"]}))
    assert sum(len(b) for b in plain.span_blobs) == sum(len(b) for b in from_otlp(_doc({"agentest.output": "x" * 400, "enduser.roles": ["admin"]})).span_blobs)
    assert plain.span_blobs.count("x" * 400) == 1
    assert aliased({"a": 1}) == {"a": 1}


def test_role_alias_reaches_the_admin_role_check(tmp_path):
    gov = {"roles": {"adminTools": ["reset_password"], "adminRoles": ["admin"]}}
    tools = {"reset_password": {"name": "reset_password", "inputSchema": {"type": "object"}, "annotations": {"readOnlyHint": False}}}
    agent = Agent("desk", tmp_path, {"name": "desk", "skills": []}, tools, gov)
    viewer = evaluate(agent, [from_otlp(_doc({"agentest.auth.role": "viewer"}))], ids=["T5-016"])["T5-016"]
    admin = evaluate(agent, [from_otlp(_doc({"enduser.roles": ["admin"]}))], ids=["T5-016"])["T5-016"]
    assert (viewer.status, admin.status) == ("fail", "pass")


def test_tool_declarations_from_meta(tmp_path):
    tools = {"open_page": {"name": "open_page", "inputSchema": {"type": "object"},
                           "_meta": {"agentest/agentest.tool.kind": "page_snapshot", "agentest/step.high_impact": True,
                                     "agentest/agentest.data.categories": ["health", "contact"], "agentest/data.sensitive": True,
                                     "agentest/data.destination_region": "eu", "agentest/agentest.step.high_impact": False,
                                     "agentest/not.declarable": 1, "other/agentest.tool.kind": "x"}},
             "plain": {"name": "plain", "inputSchema": {"type": "object"}, "_meta": "not a dict"}}
    agent = Agent("desk", tmp_path, {"name": "desk", "skills": []}, tools, {})
    assert agent.declared("open_page") == {"agentest.tool.kind": "page_snapshot", "agentest.step.high_impact": False,
                                           "agentest.data.categories": ["health", "contact"], "agentest.data.sensitive": True,
                                           "agentest.data.destination_region": "eu"}
    assert agent.declared("plain") == {} and agent.declared("unknown") == {}
    assert set(agent.declared("open_page")) <= set(DECLARABLE_ON_TOOL)
    declarable = {k for k, d in SCHEMA["x-agentest-attributes"].items() if "tool" in (d.get("declarableOn") or [])}
    assert declarable == set(DECLARABLE_ON_TOOL)


def test_span_value_overrides_the_tool_declaration(tmp_path):
    ep = Episode("desk", "case-1", 0, input="read the page")
    ep.add_tool("open_page", {"url": "https://example.invalid"}, "<html/>")
    ep.add_tool("open_page", {"url": "https://example.invalid/2"}, "<html/>")
    doc = json.loads(json.dumps(to_otlp(ep, "desk", None, [{"agentest.tool.kind": "knowledge_lookup"}, {}])))
    run = from_otlp(doc)
    raw_attrs = [dict(t.attrs) for t in run.tools]
    tools = {"open_page": {"name": "open_page", "inputSchema": {"type": "object"},
                           "_meta": {"agentest/agentest.tool.kind": "page_snapshot", "agentest/agentest.data.sensitive": True}}}
    agent = Agent("desk", tmp_path, {"name": "desk", "skills": []}, tools, {})
    evaluate(agent, [run], ids=["T1-001"])  # evaluate applies the declarations
    assert [t.attrs["agentest.tool.kind"] for t in run.tools] == ["knowledge_lookup", "page_snapshot"]
    assert all(t.attrs["agentest.data.sensitive"] is True for t in run.tools)
    apply_tool_declarations(agent, [run])  # idempotent
    assert [t.attrs["agentest.tool.kind"] for t in run.tools] == ["knowledge_lookup", "page_snapshot"]
    assert all(set(raw) <= set(t.attrs) for raw, t in zip(raw_attrs, run.tools, strict=True))
