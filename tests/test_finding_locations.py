"""Failing verdicts carry the OTel span(s) where the finding occurred (generic; no rule-specific code)."""
from agentest.standards.otel import Run
from agentest.standards.rules import locate


def _run():
    r = Run(input_id="case-1", rep=0, input="", answer="")
    r.spans = [{"id": "r" * 16, "parent": "", "tool": ""}, {"id": "a" * 16, "parent": "r" * 16, "tool": "lookup"},
               {"id": "b" * 16, "parent": "r" * 16, "tool": "pay"}]
    return r


def test_cited_span_id_wins():
    assert [x["span_id"] for x in locate(f"bad call at {'b' * 16}", [_run()])] == ["b" * 16]


def test_named_tool_span():
    loc = locate("case-1: pay(order_id) before lookup ran", [_run()])
    assert {x["span_id"] for x in loc} == {"a" * 16, "b" * 16} and all(x["how"] == "tool" for x in loc)


def test_trace_level_falls_back_to_root():
    assert locate("max tokens per run = 9999", [_run()]) == [{"span_id": "r" * 16, "trace": "case-1", "how": "root"}]
