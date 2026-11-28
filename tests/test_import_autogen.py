"""AutoGen import: the printed repr form and the ``model_dump(mode="json")`` form give the same tool spans, tool results
reach the span, a malformed log is one line (no traceback), and a tool that is not declared still fails."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentest.cli import main
from agentest.standards.importers import NativeLogError, adapt

FX = Path(__file__).resolve().parent / "fixtures" / "autogen_import"
MAP = json.loads((FX / "map.json").read_text(encoding="utf-8"))


def _import(name: str, tmp_path: Path) -> Path:
    out = tmp_path / f"{name}.otlp.jsonl"
    assert main(["std", "import", str(FX / f"native-{name}.jsonl"), "--map", str(FX / "map.json"), "--out", str(out)]) == 0
    return out


def _verdicts(otlp: Path, tmp_path: Path) -> dict:
    out = tmp_path / "v.json"
    assert main(["std", "run", "--otlp", str(otlp), "--card", str(FX / "agent-card.json"), "--tools", str(FX / "tools.json"),
                 "--format", "json", "--out", str(out)]) in (0, 1)
    return {r["id"]: r["status"] for r in json.loads(out.read_text(encoding="utf-8"))["results"]}


def _tool_spans(otlp: Path) -> dict:
    spans = {}
    for line in otlp.read_text(encoding="utf-8").splitlines():
        for rs in json.loads(line)["resourceSpans"]:
            for ss in rs["scopeSpans"]:
                for sp in ss["spans"]:
                    attrs = {a["key"]: next(iter(a["value"].values())) for a in sp["attributes"]}
                    if attrs.get("gen_ai.operation.name") == "execute_tool":
                        spans[attrs["gen_ai.tool.name"]] = attrs
    return spans


def _episode(name: str):
    raw = json.loads((FX / f"native-{name}.jsonl").read_text(encoding="utf-8"))
    return adapt(raw, MAP)


@pytest.mark.parametrize("form", ["json", "repr"])
def test_tool_spans_carry_results(form, tmp_path):
    spans = _tool_spans(_import(f"{form}-declared", tmp_path))
    assert set(spans) == {"lookup_order", "request_refund"}
    assert spans["lookup_order"]["gen_ai.tool.call.id"] == "c1"
    assert json.loads(spans["lookup_order"]["gen_ai.tool.call.arguments"]) == {"order_id": "ORD-7"}
    assert spans["lookup_order"]["gen_ai.tool.call.result"] == '{"total": 40}'
    assert spans["request_refund"]["gen_ai.tool.call.result"] == "refund issued"


def test_json_and_repr_forms_give_the_same_verdicts(tmp_path):
    assert _verdicts(_import("json-declared", tmp_path), tmp_path) == _verdicts(_import("repr-declared", tmp_path), tmp_path)


@pytest.mark.parametrize("form", ["json", "repr"])
def test_declared_tools_pass_and_an_undeclared_tool_still_fails(form, tmp_path):
    ok = _verdicts(_import(f"{form}-declared", tmp_path), tmp_path)
    bad = _verdicts(_import(f"{form}-undeclared", tmp_path), tmp_path)
    assert ok["T5-001"] == ok["T5-018"] == "pass"
    assert bad["T5-001"] == bad["T5-018"] == "fail"


@pytest.mark.parametrize("form", ["json", "repr"])
def test_error_result_marks_the_call_failed(form):
    ep = _episode(f"{form}-error-result")
    (call,) = ep.tool_calls
    assert call.error is True and call.result == "order service unavailable"


def test_a_request_without_a_result_event_still_imports():
    ep = _episode("json-call-only")
    assert [c.name for c in ep.tool_calls] == ["lookup_order", "request_refund"]
    assert all(c.result is None and not c.error for c in ep.tool_calls)


def test_result_matches_by_call_id_not_order():
    raw = {"agent": "a", "trace": [
        {"type": "ToolCallRequestEvent", "source": "a", "content": [{"id": "x1", "name": "t1", "arguments": "{}"}, {"id": "x2", "name": "t1", "arguments": "{}"}]},
        {"type": "ToolCallExecutionEvent", "source": "a", "content": [
            {"content": "second", "name": "t1", "call_id": "x2", "is_error": False},
            {"content": "first", "name": "t1", "call_id": "x1", "is_error": False}]}]}
    ep = adapt(raw, MAP)
    assert [(c.call_id, c.result) for c in ep.tool_calls] == [("x1", "first"), ("x2", "second")]


def test_result_without_call_id_matches_the_earliest_unanswered_call_of_that_name():
    raw = {"agent": "a", "trace": [
        {"type": "ToolCallRequestEvent", "source": "a", "content": [{"name": "t1", "arguments": {}}, {"name": "t1", "arguments": {}}]},
        {"type": "ToolCallExecutionEvent", "source": "a", "content": [{"content": "r1", "name": "t1"}]},
        {"type": "ToolCallExecutionEvent", "source": "a", "content": [{"content": "r2", "name": "t1"}]}]}
    assert [c.result for c in adapt(raw, MAP).tool_calls] == ["r1", "r2"]


def test_events_dialect_reads_the_json_form_and_keeps_results_off_the_reply():
    raw = {"agent": "a", "trace": [
        {"kind": "message", "name": "ToolCallRequestEvent", "data": {"source": "a", "content": [{"id": "c1", "name": "lookup_order", "arguments": "{\"order_id\": \"ORD-7\"}"}]}},
        {"kind": "message", "name": "ToolCallExecutionEvent", "data": {"source": "a", "content": [{"content": "ok", "name": "lookup_order", "call_id": "c1", "is_error": False}]}},
        {"kind": "message", "name": "TextMessage", "data": {"source": "a", "content": "Done."}}]}
    ep = adapt(raw, {"dialect": "events"})
    assert [(c.name, c.arguments, c.result) for c in ep.tool_calls] == [("lookup_order", {"order_id": "ORD-7"}, "ok")]
    assert [m.content for m in ep.messages if m.role == "assistant"] == ["Done."]


BAD = {
    "content is a number": [{"type": "ToolCallRequestEvent", "source": "a", "content": 5}],
    "call is not an object": [{"type": "ToolCallRequestEvent", "source": "a", "content": ["lookup_order"]}],
    "call has no name": [{"type": "ToolCallRequestEvent", "source": "a", "content": [{"id": "c1", "arguments": "{}"}]}],
    "result content is a number": [{"type": "ToolCallExecutionEvent", "source": "a", "content": 5}],
    "result is not an object": [{"type": "ToolCallExecutionEvent", "source": "a", "content": ["ok"]}],
}


@pytest.mark.parametrize("why", sorted(BAD))
def test_malformed_log_is_one_line_with_no_traceback(why, tmp_path, capsys):
    native = tmp_path / "bad.jsonl"
    native.write_text(json.dumps({"agent": "a", "trace": BAD[why]}) + "\n", encoding="utf-8")
    assert main(["std", "import", str(native), "--map", str(FX / "map.json"), "--out", str(tmp_path / "x.jsonl")]) == 2
    out = capsys.readouterr()
    lines = (out.out + out.err).splitlines()
    assert len(lines) == 1 and lines[0].startswith("std import: autogen ToolCall") and "Traceback" not in lines[0]
    assert not (tmp_path / "x.jsonl").exists()


@pytest.mark.parametrize("dialect,trace", [
    ("langgraph_msgs", [{"role": "ai", "tool_calls": 7}]),
    ("smolagents", [{"tool_calls": [5]}]),
    ("events", [{"kind": "message", "name": "HandoffMessage", "data": 5}]),
])
def test_a_record_of_the_wrong_shape_is_a_one_line_error_in_other_dialects_too(dialect, trace):
    with pytest.raises(NativeLogError) as e:
        adapt({"agent": "a", "trace": trace}, {"dialect": dialect})
    assert "\n" not in str(e.value) and str(e.value).startswith(f"{dialect} log is not in the expected shape")
