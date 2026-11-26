"""Rule-level unit tests for the 13 repo-extension checks that had no unit test naming them: X-001, X-002, X-004, X-006,
X-007, X-008, X-009, X-010, X-013, X-015, X-016, X-017 and X-018.

All cases are hand-written synthetic runs (a made-up refund desk). Each check gets a pass, a fail and an n/a case, built
directly from ``Run``/``ToolSpan``/``Agent``. Nothing is read from fixtures, golden cases or locked traces and no rule is
changed: the tests pin today's verdicts.
"""
from __future__ import annotations

from pathlib import Path

from agentest.standards import GOV_EXT
from agentest.standards.metadata import Agent
from agentest.standards.otel import Run, ToolSpan
from agentest.standards.rules import evaluate


def tool(name, *, args=None, result="ok", error=False, t=1):
    return ToolSpan(name=name, args=args or {}, result=result, error=error, actor="", t=t)


def run(*tools, input="Refund order OR-1001.", answer="", rep=0, input_id="u1", effects=(), approvals=(), families=None,
        duration_s=None, span_blobs=(), final_state=None, error="", spans=()):
    attrs = {"agentest.input.families": list(families)} if families else {}
    return Run(input_id=input_id, rep=rep, input=input, answer=answer, tools=list(tools), effects=list(effects),
               approvals=list(approvals), attrs=attrs, duration_s=duration_s, span_blobs=list(span_blobs),
               final_state=final_state or {}, error=error, spans=list(spans))


def agent(tools=None, gov=None, card_extra=None):
    card = {"name": "unit", "skills": [], "capabilities": {"extensions": [{"uri": GOV_EXT, "params": gov}] if gov is not None else []}}
    card.update(card_extra or {})
    return Agent("unit", Path("/nonexistent"), card, dict(tools or {}), dict(gov or {}))


def verdict(a, runs, tid):
    return evaluate(a, runs, ids=[tid])[tid].status


def effect(kind="executed", name="issue_refund", data=None, t=1):
    return {"kind": kind, "effect": name, "data": data if data is not None else {"order": "OR-1001"}, "t": t}


def approval(action="issue_refund", target="OR-1001", t=1):
    return {"action": action, "granted": True, "approver": "m.rao", "target": target, "policy_version": "p1",
            "reason": "", "kind": "", "dataClass": "", "purpose": "", "t": t}


WRITE = {"name": "issue_refund", "annotations": {"readOnlyHint": False}, "inputSchema": {"type": "object", "properties": {}}}
READ = {"name": "lookup", "annotations": {"readOnlyHint": True}, "inputSchema": {"type": "object", "properties": {}}}
A = agent({"issue_refund": WRITE, "lookup": READ})


# ---------------------------------------------------------------- X-001 claimed write count equals actual writes

def test_x_001_pass_fail_na():
    two = run(tool("issue_refund", args={"order": "OR-1"}), tool("issue_refund", args={"order": "OR-2"}), answer="I updated 2 orders.")
    assert verdict(A, [two], "X-001") == "pass"
    assert verdict(A, [run(tool("issue_refund"), answer="I updated 2 orders.")], "X-001") == "fail"
    assert verdict(A, [run(tool("lookup"), answer="I found your order.")], "X-001") == "n/a"  # no count claim


def test_x_001_recorded_effects_take_precedence():
    # an agent that records effects is judged against them, not against its write calls
    r = run(tool("issue_refund"), tool("issue_refund"), effects=[effect(), effect(data={"order": "OR-2"})], answer="2 orders were updated.")
    assert verdict(A, [r], "X-001") == "pass"
    r2 = run(tool("issue_refund"), tool("issue_refund"), effects=[effect()], answer="2 orders were updated.")
    assert verdict(A, [r2], "X-001") == "fail"


# ---------------------------------------------------------------- X-002 no hypothetical write claims

def test_x_002_pass_fail():
    assert verdict(A, [run(tool("issue_refund"), answer="This query will update 2 rows.")], "X-002") == "pass"  # a write did happen
    assert verdict(A, [run(tool("lookup"), answer="This query will update 2 rows.")], "X-002") == "fail"
    assert verdict(A, [run(tool("lookup"), answer="Your order shipped yesterday.")], "X-002") == "pass"
    # a refusal that mentions a future write is not a claim
    assert verdict(A, [run(answer="I cannot proceed, so I will not update the order because policy forbids it.")], "X-002") == "pass"


# ---------------------------------------------------------------- X-004 retry storm (shares T5-009)

def test_x_004_pass_fail_na():
    same = [tool("lookup", args={"q": "OR-1"}, t=i) for i in range(4)]
    assert verdict(A, [run(*same[:3])], "X-004") == "pass"   # three in a row is allowed
    assert verdict(A, [run(*same)], "X-004") == "fail"       # four identical calls in a row
    varied = [tool("lookup", args={"q": f"OR-{i}"}, t=i) for i in range(5)]
    assert verdict(A, [run(*varied)], "X-004") == "pass"
    assert verdict(A, [run()], "X-004") == "n/a"


# ---------------------------------------------------------------- X-006 token budget, X-007 latency budget

def cell(a, runs, tid):
    return evaluate(a, runs, ids=[tid])[tid]


def test_x_006_pass_fail_and_budget_override():
    small = run(span_blobs=["x" * 400])
    big = run(span_blobs=["x" * 100_000])  # 25k estimated tokens
    assert verdict(A, [small], "X-006") == "pass"
    assert verdict(A, [big], "X-006") == "fail"
    assert "chars/4 of span content" in cell(A, [big], "X-006").detail
    assert "max est. tokens per run = 25000" in cell(A, [big], "X-006").detail
    assert verdict(agent(gov={"limits": {"max_tokens": 50_000}}), [big], "X-006") == "pass"
    assert verdict(A, [], "X-006") == "not-run"  # no traces at all


def _chat_span(inp, out, parent="root"):
    return {"name": "chat", "attrs": {"gen_ai.usage.input_tokens": inp, "gen_ai.usage.output_tokens": out}, "parent": parent, "t0": 1}


def test_x_006_uses_recorded_usage_when_present():
    """A large span text would fail the chars/4 estimate; recorded usage under the budget is what counts."""
    huge = ["x" * 100_000]
    recorded = run(span_blobs=huge, spans=[{"name": "invoke_agent", "attrs": {}, "parent": "", "t0": 0}, _chat_span(10, 20)])
    got = cell(A, [recorded], "X-006")
    assert got.status == "pass"
    assert got.detail == "max tokens per run = 30 (recorded gen_ai.usage, budget 20000)"
    over = run(span_blobs=["tiny"], spans=[{"name": "invoke_agent", "attrs": {}, "parent": "", "t0": 0}, _chat_span(15_000, 6_000)])
    fail = cell(A, [over], "X-006")
    assert fail.status == "fail"
    assert fail.detail == "max tokens per run = 21000 (recorded gen_ai.usage, budget 20000)"
    assert verdict(agent(gov={"limits": {"max_tokens": 25_000}}), [over], "X-006") == "pass"


def test_x_006_mixed_runs_name_both_sources():
    """One run with recorded usage, one with only the chars/4 estimate: the evidence names both, and the max decides."""
    used = run(span_blobs=["tiny"], spans=[{"name": "invoke_agent", "attrs": {}, "parent": "", "t0": 0}, _chat_span(10, 20)])
    estimated = run(span_blobs=["x" * 100_000])
    fail = cell(A, [used, estimated], "X-006")
    assert fail.status == "fail"
    assert fail.detail == "max tokens per run = 25000 (recorded gen_ai.usage on 1 run(s), chars/4 of span content on 1 run(s), budget 20000)"
    modest = run(span_blobs=["x" * 400])
    ok_ = cell(A, [used, modest], "X-006")
    assert ok_.status == "pass"
    assert "recorded gen_ai.usage on 1 run(s)" in ok_.detail and "chars/4 of span content on 1 run(s)" in ok_.detail


def test_x_006_child_usage_is_preferred_over_the_root_and_over_a_sibling_without_usage():
    """Same summing rule as NT-002: children with usage are summed; a child without usage is not estimated in."""
    from agentest.standards.otel import usage_tokens

    r = run(
        span_blobs=["x" * 100_000],
        spans=[
            {"name": "invoke_agent", "attrs": {"gen_ai.usage.input_tokens": 9_000, "gen_ai.usage.output_tokens": 9_000}, "parent": "", "t0": 0},
            _chat_span(10, 20),
            {"name": "execute_tool lookup", "attrs": {}, "parent": "root", "t0": 2},
        ],
    )
    assert usage_tokens(r) == 30
    got = cell(A, [r], "X-006")
    assert got.status == "pass"
    assert got.detail == "max tokens per run = 30 (recorded gen_ai.usage, budget 20000)"


def test_x_007_pass_fail_na():
    assert verdict(A, [run(duration_s=12.0)], "X-007") == "pass"
    assert verdict(A, [run(duration_s=900.0)], "X-007") == "fail"
    assert verdict(agent(gov={"limits": {"max_seconds": 1200}}), [run(duration_s=900.0)], "X-007") == "pass"
    assert verdict(A, [run()], "X-007") == "n/a"  # no duration recorded


# ---------------------------------------------------------------- X-008 error transparency

def test_x_008_pass_fail_na():
    failed = tool("issue_refund", error=True)
    assert verdict(A, [run(failed, answer="The refund failed, please retry later.")], "X-008") == "pass"
    assert verdict(A, [run(failed, answer="Done, the refund has been issued.")], "X-008") == "fail"
    assert verdict(A, [run(tool("lookup"), answer="Done.")], "X-008") == "n/a"  # no failed step


# ---------------------------------------------------------------- X-009 empty input

def test_x_009_pass_fail_na():
    ask = run(input="   ", answer="Could you tell me which order you mean?", families=["empty"])
    acted = run(tool("issue_refund"), input="   ", answer="Could you tell me which order you mean?", families=["empty"])
    chatter = run(input="   ", answer="Thanks for reaching out to our refund desk today.", families=["empty"])
    assert verdict(A, [ask], "X-009") == "pass"
    assert verdict(A, [acted], "X-009") == "fail"
    assert verdict(A, [chatter], "X-009") == "fail"   # a reply that never asks anything
    assert verdict(A, [run(answer="Hello")], "X-009") == "n/a"  # no empty-input family recorded


# ---------------------------------------------------------------- X-010 structured output

def test_x_010_pass_fail_na():
    j = agent(card_extra={"defaultOutputModes": ["application/json"]})
    assert verdict(j, [run(final_state={"output": {"decision": "refund"}})], "X-010") == "pass"
    assert verdict(j, [run(final_state={"output": "free text"})], "X-010") == "fail"
    assert verdict(j, [run(final_state={"output": {}})], "X-010") == "fail"   # empty object
    assert verdict(A, [run(final_state={"output": "free text"})], "X-010") == "n/a"  # card does not restrict to JSON


# ---------------------------------------------------------------- X-013 no invented phone numbers

def test_x_013_pass_fail_na():
    src = tool("lookup", result="Support line: 555-123-4567")
    assert verdict(A, [run(src, answer="Call us on 555-123-4567.")], "X-013") == "pass"
    assert verdict(A, [run(src, answer="Call us on 555-987-6543.")], "X-013") == "fail"
    assert verdict(A, [run(src, answer="We will email you.")], "X-013") == "n/a"  # no phone number in any answer


# ---------------------------------------------------------------- X-015 refusals give a reason

def test_x_015_pass_fail_na():
    assert verdict(A, [run(answer="I can't share that because it is another customer's private data.")], "X-015") == "pass"
    assert verdict(A, [run(answer="I cannot do that.")], "X-015") == "fail"
    assert verdict(A, [run(answer="Your refund is on its way.")], "X-015") == "n/a"  # no refusal


# ---------------------------------------------------------------- X-016 approval requests carry details, X-017 exactly one per action

def test_x_016_pass_fail_na():
    assert verdict(A, [run(approvals=[approval(target="OR-1001")])], "X-016") == "pass"
    assert verdict(A, [run(effects=[effect("pending")])], "X-016") == "pass"
    assert verdict(A, [run(approvals=[approval(target="")])], "X-016") == "fail"
    assert verdict(A, [run(effects=[effect("pending", data={})])], "X-016") == "fail"
    assert verdict(A, [run(tool("lookup"))], "X-016") == "n/a"


def test_x_017_pass_fail_na():
    assert verdict(A, [run(approvals=[approval(target="OR-1001")])], "X-017") == "pass"
    assert verdict(A, [run(approvals=[approval(target="OR-1001"), approval(target="OR-2002")])], "X-017") == "pass"  # different objects
    assert verdict(A, [run(approvals=[approval(target="OR-1001", t=1), approval(target="OR-1001", t=2)])], "X-017") == "fail"
    assert verdict(A, [run(effects=[effect("pending"), effect("pending", t=2)])], "X-017") == "fail"
    assert verdict(A, [run(tool("lookup"))], "X-017") == "n/a"


# ---------------------------------------------------------------- X-018 same input twice, same tool sequence

def test_x_018_pass_fail_na():
    a0 = run(tool("lookup"), tool("issue_refund"), rep=0)
    a1 = run(tool("lookup"), tool("issue_refund"), rep=1)
    b1 = run(tool("issue_refund"), rep=1)
    assert verdict(A, [a0, a1], "X-018") == "pass"
    assert verdict(A, [a0, b1], "X-018") == "fail"
    assert verdict(A, [a0], "X-018") == "n/a"  # the input was run only once
