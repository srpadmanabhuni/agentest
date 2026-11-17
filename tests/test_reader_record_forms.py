"""Trace format D8: a record read as a dedicated span, a span event or an OTLP log record gives the same run and the
same verdicts. Bundled traces already use the read form, so lifting leaves every one of them as it is."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from agentest.standards import metadata
from agentest.standards.catalog import ALL_IDS, RAI_ADDITION_IDS
from agentest.standards.episode import Episode
from agentest.standards.metadata import Agent
from agentest.standards.otel import EVENT_RECORDS, SPAN_RECORDS, _attrs, from_otlp, lift_records, read_otlp_file, split_traces, to_otlp
from agentest.standards.rules import evaluate
from agentest.standards.runner import otlp_docs
from tests import bundled_verdicts as bv

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_TEXT = (ROOT / "src/agentest/standards/schemas/trace-format.schema.json").read_text(encoding="utf-8")
IDS = list(ALL_IDS) + [i for i in RAI_ADDITION_IDS if i not in ALL_IDS]
GOV = {"approval": {"required": ["request_refund"]}, "limits": {"max_amount": 500}}
TOOLS = {"lookup_order": {"name": "lookup_order", "inputSchema": {"type": "object"}, "annotations": {"readOnlyHint": True}},
         "request_refund": {"name": "request_refund", "inputSchema": {"type": "object"}, "annotations": {"readOnlyHint": False, "destructiveHint": True}}}


def _reference() -> list[dict]:
    docs = []
    for rep, granted in enumerate((True, True, False)):
        ep = Episode("desk", "refund", rep, input="Refund order ORD-7", final_answer="Your refund for ORD-7 was issued.")
        ep.add_tool("lookup_order", {"order_id": "ORD-7"}, {"total": 40})
        ep.add_tool("request_refund", {"order_id": "ORD-7", "amount": 40}, {"status": "issued"})
        ep.approval("request_refund", granted, approver="ops")
        ep.state_changes.append(__import__("agentest.standards.episode", fromlist=["StateChange"]).StateChange("executed", "request_refund",
                                                                                                          {"order_id": "ORD-7", "amount": 40}))
        docs.append(json.loads(json.dumps(to_otlp(ep, "desk", None, None, [{"gen_ai.evaluation.name": "harness", "gen_ai.evaluation.score.label": "pass"}]))))
    return docs


def _spans(doc: dict) -> list[dict]:
    return doc["resourceSpans"][0]["scopeSpans"][0]["spans"]


def _root(doc: dict) -> dict:
    return next(s for s in _spans(doc) if not s.get("parentSpanId"))


def _log(doc: dict, name: str, attrs: list, t: str, span_id: str = "", in_body: bool = False) -> dict:
    lr = {"timeUnixNano": t, "traceId": _root(doc)["traceId"], "spanId": span_id or _root(doc)["spanId"]}
    if in_body:
        lr.update({"attributes": [{"key": "event.name", "value": {"stringValue": name}}], "body": {"kvlistValue": {"values": attrs}}})
    else:
        lr.update({"eventName": name, "attributes": attrs})
    doc.setdefault("resourceLogs", []).append({"scopeLogs": [{"logRecords": [lr]}]})
    return doc


def _approval_as(doc: dict, form: str) -> dict:
    doc = copy.deepcopy(doc)
    spans = _spans(doc)
    ap = next(s for s in spans if s["name"] == "agentest.approval")
    spans.remove(ap)
    if form == "event":
        carrier = next(s for s in spans if s.get("spanId") == ap["parentSpanId"])
        carrier.setdefault("events", []).append({"name": "agentest.approval", "timeUnixNano": ap["startTimeUnixNano"], "attributes": ap["attributes"]})
    else:
        _log(doc, "agentest.approval", ap["attributes"], ap["startTimeUnixNano"], ap["parentSpanId"], in_body=form == "log-body")
    return doc


def _root_event_as(doc: dict, name: str, form: str) -> dict:
    doc = copy.deepcopy(doc)
    root = _root(doc)
    ev = next(e for e in root["events"] if e["name"] == name)
    root["events"].remove(ev)
    child = next(s for s in _spans(doc) if s.get("parentSpanId"))
    if form == "span":
        _spans(doc).append({"traceId": root["traceId"], "spanId": "cd" * 8, "parentSpanId": root["spanId"], "name": name, "kind": 1,
                            "startTimeUnixNano": ev["timeUnixNano"], "endTimeUnixNano": ev["timeUnixNano"], "attributes": ev["attributes"]})
    elif form == "child-event":
        child.setdefault("events", []).append(ev)
    else:
        _log(doc, name, ev["attributes"], ev["timeUnixNano"], in_body=form == "log-body")
    return doc


def _view(doc: dict) -> tuple:
    r = from_otlp(json.loads(json.dumps(doc)))
    return ([{k: v for k, v in a.items()} for a in r.approvals], r.effects, r.evaluations, [(t.name, t.args, t.result) for t in r.tools], r.answer)


def _verdicts(tmp: Path, docs: list[dict]) -> dict:
    agent = Agent("desk", tmp, {"name": "desk", "skills": []}, TOOLS, GOV)
    return {k: v.status for k, v in evaluate(agent, [from_otlp(json.loads(json.dumps(d))) for d in docs], ids=IDS).items()}


def test_record_names_cover_the_schema():
    schema = json.loads(SCHEMA_TEXT)
    names = {c["if"]["properties"][k]["const"] for d in ("span", "event", "logRecord") for c in schema["$defs"][d].get("allOf", [])
             for k in ("name", "eventName") if "const" in c.get("if", {}).get("properties", {}).get(k, {})}
    assert names and names <= set(SPAN_RECORDS) | set(EVENT_RECORDS)
    assert not set(SPAN_RECORDS) & set(EVENT_RECORDS) and len(SPAN_RECORDS) + len(EVENT_RECORDS) == 14
    doc_text = (ROOT / "docs" / "TRACE-FORMAT.md").read_text(encoding="utf-8")
    assert all(f"`{n}`" in doc_text for n in (*SPAN_RECORDS, *EVENT_RECORDS))


def test_approval_as_event_or_log_reads_like_the_span(tmp_path):
    ref = _reference()
    assert any(_view(d)[0] for d in ref)
    want = _verdicts(tmp_path, ref)
    for form in ("event", "log", "log-body"):
        docs = [_approval_as(d, form) for d in ref]
        assert [_view(d)[0] for d in docs] == [_view(d)[0] for d in ref], form
        assert _verdicts(tmp_path, docs) == want, form


def test_state_change_and_evaluation_in_every_form(tmp_path):
    ref = _reference()
    want = _verdicts(tmp_path, ref)
    for name in EVENT_RECORDS:
        for form in ("span", "child-event", "log", "log-body"):
            docs = [_root_event_as(d, name, form) for d in ref]
            assert [_view(d)[1:3] for d in docs] == [_view(d)[1:3] for d in ref], (name, form)
            assert _verdicts(tmp_path, docs) == want, (name, form)


def test_span_records_from_events_and_logs_become_child_spans():
    doc = copy.deepcopy(_reference()[0])
    tool = next(s for s in _spans(doc) if s["name"].startswith("execute_tool"))
    tool["events"] = [{"name": "agentest.human_input", "timeUnixNano": tool["startTimeUnixNano"], "attributes": _attrs({"agentest.human_input.kind": "correction"})}]
    _log(doc, "agentest.notice", _attrs({"agentest.notice.channel": "email"}), tool["endTimeUnixNano"])
    _log(doc, "unrelated.log", _attrs({"x": 1}), tool["endTimeUnixNano"])
    out = _spans(lift_records(doc))
    hi = next(s for s in out if s["name"] == "agentest.human_input")
    no = next(s for s in out if s["name"] == "agentest.notice")
    assert hi["parentSpanId"] == tool["spanId"] and hi["attributes"][0]["key"] == "agentest.human_input.kind"
    assert no["parentSpanId"] == _root(doc)["spanId"] and not any(s["name"] == "unrelated.log" for s in out)
    assert len(out) == len(_spans(doc)) + 2


def test_log_records_of_another_trace_are_ignored_and_files_merge_logs(tmp_path):
    ref = _reference()
    doc = _approval_as(ref[0], "log")
    doc["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]["traceId"] = "f" * 32
    assert _view(doc)[0] == []
    logs_only = {"resourceLogs": _approval_as(ref[0], "log")["resourceLogs"]}
    spans_only = {k: v for k, v in _approval_as(ref[0], "log").items() if k != "resourceLogs"}
    f = tmp_path / "t.otlp.jsonl"
    f.write_text(json.dumps(spans_only) + "\n" + json.dumps(logs_only) + "\n", encoding="utf-8")
    docs = read_otlp_file(f)
    assert len(docs) == 1 and _view(docs[0])[0] == _view(ref[0])[0]
    assert len(split_traces({"resourceSpans": spans_only["resourceSpans"], "resourceLogs": logs_only["resourceLogs"]})) == 1


def test_bundled_traces_are_already_in_the_read_form():
    n = 0
    for d in bv.agent_dirs():
        assert d not in bv.EXCLUDED_PATHS and d.name not in bv.EXCLUDED_NAMES
        for doc in otlp_docs(metadata.load(d)):
            n += 1
            assert lift_records(doc) is doc
    assert n > 1000
