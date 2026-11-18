"""X-003 scores a tool-call reason by specificity. Length is only a fallback.

Three synthetic calls: a short reason that names an identifier from the call's arguments or the user input passes;
a long generic sentence fails; a placeholder fails. The check does not name an agent and has no random step.
"""
from __future__ import annotations

from pathlib import Path

from agentest.standards import GOV_EXT
from agentest.standards.metadata import Agent
from agentest.standards.otel import Run, ToolSpan
from agentest.standards.rules import evaluate


def tool(name, *, args=None, result="ok", error=False, attrs=None, t=1):
    return ToolSpan(name=name, args=args or {}, result=result, error=error, actor="", t=t, attrs=attrs or {})


def run(*tools, input="please help", answer="done", attrs=None, input_id="u1"):
    return Run(input_id=input_id, rep=0, input=input, answer=answer, tools=list(tools), attrs=attrs or {})


def agent(tools=None, gov=None):
    card = {"name": "unit", "skills": [], "capabilities": {"extensions": [{"uri": GOV_EXT, "params": gov}] if gov is not None else []}}
    return Agent("unit", Path("/nonexistent"), card, dict(tools or {}), dict(gov or {}))


def verdict(a, runs, tid):
    return evaluate(a, runs, ids=[tid])[tid].status


READER = {"name": "lookup", "annotations": {"readOnlyHint": True}, "inputSchema": {"type": "object", "properties": {}}}
A = agent({"lookup": READER, "issue_refund": READER})


def test_x_003_short_reason_with_identifier_passes():
    # under the old 12-character floor, but the reason names the order on the call
    refund = run(tool("issue_refund", args={"order_id": "ORD-7", "reason": "ORD-7"}), input="please refund that order")
    assert verdict(A, [refund], "X-003") == "pass"
    # the same identifier can come from the user input when no other argument repeats it
    from_input = run(tool("issue_refund", args={"reason": "ORD-7"}), input="refund ORD-7")
    assert verdict(A, [from_input], "X-003") == "pass"
    # the issue's sample wording also names the order
    phrased = run(tool("issue_refund", args={"order_id": "ORD-7", "reason": "refund ORD-7"}), input="please refund that order")
    assert verdict(A, [phrased], "X-003") == "pass"
    looked_up = run(tool("lookup", args={"code": "KC-52"}, attrs={"agentest.tool.reason": "KC-52"}), input="look up the case")
    assert verdict(A, [looked_up], "X-003") == "pass"
    # an identifier that appears only inside the reason, not in the other arguments or the user input, is not specific
    invented = run(tool("lookup", args={"reason": "ORD-7"}), input="please help")
    assert verdict(A, [invented], "X-003") == "fail"


def test_x_003_long_generic_filler_fails():
    generic = "The model selected this tool call for the request and will use the data."
    assert verdict(A, [run(tool("lookup", args={"reason": generic}))], "X-003") == "fail"
    labelled = "crm: model-selected tool call"
    assert verdict(A, [run(tool("lookup", attrs={"agentest.tool.reason": labelled}))], "X-003") == "fail"
    # a long reason that says what is being checked is still specific
    specific = run(tool("lookup", args={"reason": "verify the order is within the return window"}))
    assert verdict(A, [specific], "X-003") == "pass"
    assert verdict(A, [specific], "T5-015") == "pass"


def test_x_003_placeholder_fails():
    for text in ("n/a", "task", "tool call"):
        assert verdict(A, [run(tool("lookup", args={"reason": text}))], "X-003") == "fail", text
    # T5-015 only requires a reason to be present; quality is X-003
    assert verdict(A, [run(tool("lookup", args={"reason": "n/a"}))], "T5-015") == "pass"
    assert verdict(A, [run(tool("lookup", args={"reason": "check"}))], "X-003") == "fail"
    assert verdict(A, [run()], "X-003") == "n/a"
