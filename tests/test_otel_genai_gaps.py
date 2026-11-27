"""Gaps found when the importer was checked against the pinned OpenTelemetry GenAI conventions
(docs/integrations/otel-genai-compatibility.md): each one is filled here, and each gives the verdicts of the
equivalent trace written the usual way. Verdict semantics of the existing traces do not change."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from agentest.standards import otel
from tests.test_otel_conformance import ANSWER, ASK, ROOT, _doc, _span, _verdicts, otel_current

REPO = Path(__file__).resolve().parents[1]
DETAILS = "gen_ai.client.inference.operation.details"


def _any(v):
    """Python value -> OTLP AnyValue, structured (kvlist / array) the way a current instrumentation sends it."""
    if isinstance(v, bool):
        return {"boolValue": v}
    if isinstance(v, int):
        return {"intValue": str(v)}
    if isinstance(v, dict):
        return {"kvlistValue": {"values": [{"key": k, "value": _any(x)} for k, x in v.items()]}}
    if isinstance(v, (list, tuple)):
        return {"arrayValue": {"values": [_any(x) for x in v]}}
    return {"stringValue": str(v)}


def _attrs(d: dict) -> list[dict]:
    return [{"key": k, "value": _any(v)} for k, v in d.items()]


def _strip(span: dict, *keys: str) -> dict:
    span["attributes"] = [a for a in span["attributes"] if a["key"] not in keys]
    return span


def _root(doc: dict) -> dict:
    return doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]


MESSAGES = ("gen_ai.input.messages", "gen_ai.output.messages")


def _content(doc: dict) -> dict:
    root = _root(doc)
    return {a["key"]: a["value"]["stringValue"] for a in root["attributes"] if a["key"] in MESSAGES}


# ---------------------------------------------------------------- structured values (JSON-schema attributes are not JSON text)

def test_structured_tool_result_is_kept_as_json_text():
    doc = otel_current()
    tool = doc["resourceSpans"][0]["scopeSpans"][0]["spans"][2]
    _strip(tool, "gen_ai.tool.call.result", "gen_ai.tool.call.arguments")
    tool["attributes"] += _attrs({"gen_ai.tool.call.arguments": {"queue": "billing"}, "gen_ai.tool.call.result": {"ticket": "K-9", "tags": ["a", "b"]}})
    t = next(x for x in otel.from_otlp(doc).tools if x.call_id == "c2")
    assert t.args == {"queue": "billing"}
    assert json.loads(t.result) == {"ticket": "K-9", "tags": ["a", "b"]}


@pytest.mark.parametrize("value", [[1, 2], ["billing"], "not json", 7])
def test_non_object_tool_arguments_do_not_raise(value):
    doc = otel_current()
    tool = _strip(doc["resourceSpans"][0]["scopeSpans"][0]["spans"][1], "gen_ai.tool.call.arguments")
    tool["attributes"] += _attrs({"gen_ai.tool.call.arguments": value})
    first = otel.from_otlp(doc).tools[0]
    assert isinstance(first.args, dict) and first.name == "lookup"


def test_structured_messages_and_tool_values_give_the_same_verdicts(tmp_path):
    doc = otel_current()
    spans = doc["resourceSpans"][0]["scopeSpans"][0]["spans"]
    for s in spans:
        for a in s["attributes"]:
            if a["key"] in MESSAGES or a["key"] in ("gen_ai.tool.call.arguments", "gen_ai.tool.call.result"):
                a["value"] = _any(json.loads(a["value"]["stringValue"]))
    assert _verdicts(tmp_path / "s", doc) == _verdicts(tmp_path / "w", otel_current())


# ---------------------------------------------------------------- content on the operation.details event

def _details_attrs(doc: dict) -> list[dict]:
    got = _content(doc)
    return [{"key": k, "value": {"stringValue": v}} for k, v in got.items()]


def test_operation_details_span_event_gives_the_same_verdicts(tmp_path):
    doc = otel_current()
    root = _strip(_root(doc), *MESSAGES)
    root["events"] = [{"name": DETAILS, "timeUnixNano": "1000", "attributes": _details_attrs(otel_current())}]
    run = otel.from_otlp(doc)
    assert run.input == ASK and run.answer == ANSWER
    assert _verdicts(tmp_path / "e", doc) == _verdicts(tmp_path / "w", otel_current())


def test_operation_details_log_record_gives_the_same_verdicts(tmp_path):
    doc = otel_current()
    root = _strip(_root(doc), *MESSAGES)
    doc["resourceLogs"] = [{"scopeLogs": [{"logRecords": [{"eventName": DETAILS, "timeUnixNano": "1000", "traceId": root["traceId"],
                                                           "spanId": root["spanId"], "attributes": _details_attrs(otel_current())}]}]}]
    [one] = otel.split_traces(doc)  # what `std serve` and `--otlp` keep
    run = otel.from_otlp(one)
    assert run.input == ASK and run.answer == ANSWER
    assert _verdicts(tmp_path / "l", doc) == _verdicts(tmp_path / "w", otel_current())


def test_operation_details_log_record_with_structured_messages():
    doc = otel_current()
    root = _strip(_root(doc), *MESSAGES)
    want = _content(otel_current())
    doc["resourceLogs"] = [{"scopeLogs": [{"logRecords": [{"attributes": _attrs({
        "event.name": DETAILS, **{k: json.loads(v) for k, v in want.items()}}), "traceId": root["traceId"], "spanId": root["spanId"]}]}]}]
    run = otel.from_otlp(otel.split_traces(doc)[0])
    assert run.input == ASK and run.answer == ANSWER


def test_span_attribute_wins_over_the_details_event():
    doc = otel_current()
    root = _root(doc)
    root["events"] = [{"name": DETAILS, "timeUnixNano": "1000", "attributes": [
        {"key": "gen_ai.output.messages", "value": {"stringValue": json.dumps([{"role": "assistant", "parts": [{"type": "text", "content": "other"}]}])}}]}]
    assert otel.from_otlp(doc).answer == ANSWER


def test_details_event_of_another_span_is_not_merged():
    doc = otel_current()
    tool = doc["resourceSpans"][0]["scopeSpans"][0]["spans"][1]
    tool["events"] = [{"name": DETAILS, "timeUnixNano": "1000", "attributes": [
        {"key": "gen_ai.output.messages", "value": {"stringValue": json.dumps([{"role": "assistant", "parts": [{"type": "text", "content": "x"}]}])}}]}]
    assert otel.from_otlp(doc).answer == ANSWER


def test_a_document_without_details_events_is_returned_as_it_is():
    doc = otel_current()
    assert otel.lift_records(doc) is doc


# ---------------------------------------------------------------- transfer, realtime, replaced names

def _agents(*spans):
    root = _span(0, "", "invoke_agent triage", {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "triage"})
    return _doc([root, *spans])


def test_transfer_tool_span_is_a_handoff():
    t = _span(1, ROOT, "execute_tool transfer_to_billing", {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "transfer_to_billing",
                                                           "gen_ai.agent.name": "triage", "gen_ai.transfer.target.name": "billing",
                                                           "gen_ai.transfer.mode": "handoff"})
    run = otel.from_otlp(_agents(t))
    assert [(s, d) for s, d, _ in run.handoffs] == [("triage", "billing")]
    assert [x.name for x in run.tools] == ["transfer_to_billing"]  # still a recorded tool call


def test_transfer_span_without_its_own_agent_name_uses_the_root_agent():
    t = _span(1, ROOT, "execute_tool t", {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "t", "gen_ai.transfer.target.name": "billing"})
    assert [(s, d) for s, d, _ in otel.from_otlp(_agents(t)).handoffs] == [("triage", "billing")]


def test_declared_handoff_source_is_not_doubled_by_a_transfer_span():
    t = _span(1, ROOT, "execute_tool t", {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "t", "gen_ai.transfer.target.name": "billing",
                                         "agentest.handoff.source": "triage"})
    assert otel.from_otlp(_agents(t)).handoffs == []  # the agentest record (an invoke_agent span) carries it


def test_plain_tool_span_is_not_a_handoff():
    t = _span(1, ROOT, "execute_tool lookup", {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "lookup"})
    assert otel.from_otlp(_agents(t)).handoffs == []


def test_realtime_inference_is_a_model_call():
    msg = json.dumps([{"role": "assistant", "parts": [{"type": "text", "content": "hello"}]}])
    c = _span(1, ROOT, "realtime_inference m", {"gen_ai.operation.name": "realtime_inference", "gen_ai.output.messages": msg})
    assert otel.from_otlp(_agents(c)).chats == ["hello"]


@pytest.mark.parametrize("old,new,value", [("gen_ai.workflow.name", "gen_ai.agent.name", "flow"),
                                           ("gen_ai.usage.cache_creation.input_tokens", "gen_ai.usage.cache_write.input_tokens", 4)])
def test_names_replaced_upstream_are_mapped(old, new, value):
    assert otel.normalize({old: value})[new] == value
    assert otel.normalize({old: value, new: "kept"})[new] == "kept"


# ---------------------------------------------------------------- the compatibility matrix

def _script():
    spec = importlib.util.spec_from_file_location("otel_genai_matrix", REPO / "scripts" / "otel_genai_matrix.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_matrix_page_is_current_and_rows_resolve():
    m = _script()
    assert m.check(m.load(), m.rule_fields(), None) == []


def test_matrix_pin_matches_semconv_yaml_and_is_a_commit():
    m = _script().load()["pinned"]
    p = otel.semconv()["pinned"]
    assert m["commit"] == p["genai_commit"] and len(m["commit"]) == 40 and int(m["commit"], 16) >= 0
    assert m["release"] == p["genai_release"]


def test_matrix_counts_add_up():
    m = _script()
    data = m.load()
    n = m.counts(data["rows"])
    assert sum(sum(v.values()) for v in n.values()) == len(data["rows"])
    assert {r["status"] for r in data["rows"]} == {"read", "partial", "not-read"}
    page = (REPO / "docs" / "integrations" / "otel-genai-compatibility.md").read_text(encoding="utf-8")
    assert f"**{len(data['rows'])}**" in page


def test_matrix_page_follows_the_wording_rules():
    page = (REPO / "docs" / "integrations" / "otel-genai-compatibility.md").read_text(encoding="utf-8").lower()
    for word in ("synthetic", "fork", "best", "leading", "fastest", "state of the art"):
        assert word not in page, word
    assert "\npip install agentest-ai\n" in page
    assert "aiensured agentest, an agentic ai testing platform" in page


def test_matrix_check_reports_a_row_the_model_lacks(tmp_path):
    m = _script()
    data = copy.deepcopy(m.load())
    data["rows"].append({"kind": "attribute", "name": "gen_ai.not_in_the_model", "status": "not-read", "how": "x"})
    assert any("gen_ai.not_in_the_model" in e or "out of date" in e for e in m.check(data, m.rule_fields(), None))
