"""Rule-level unit tests for the non-core fault-handling and memory checks T1-008, T1-012, T1-017, T6-004, T6-011 and T6-013.

All cases are hand-written synthetic runs (a made-up refund desk). Each check gets a pass, a fail and an n/a case, built
directly from ``Run``/``ToolSpan``/``Agent``; multi-turn cases share ``Run.conversation`` and are ordered by ``t0``. Nothing is
read from fixtures, golden cases or locked traces and no rule is changed: the tests pin today's verdicts.
"""
from __future__ import annotations

from pathlib import Path

from agentest.standards import GOV_EXT
from agentest.standards.metadata import Agent
from agentest.standards.otel import Run, ToolSpan
from agentest.standards.rules import evaluate


def tool(name, *, args=None, result="ok", error=False, t=1):
    return ToolSpan(name=name, args=args or {}, result=result, error=error, actor="", t=t)


def run(*tools, input="Refund order OR-1001.", answer="", input_id="u1", conversation="", t0=0, effects=(), families=None,
        canaries=(), final_state=None):
    attrs = {}
    if families:
        attrs["agentest.input.families"] = list(families)
    if canaries:
        attrs["agentest.test.canaries"] = list(canaries)
    return Run(input_id=input_id, rep=0, input=input, answer=answer, tools=list(tools), effects=list(effects), attrs=attrs,
               conversation=conversation, t0=t0, final_state=final_state or {})


def agent(tools=None, gov=None):
    card = {"name": "unit", "skills": [], "capabilities": {"extensions": [{"uri": GOV_EXT, "params": gov}] if gov is not None else []}}
    return Agent("unit", Path("/nonexistent"), card, dict(tools or {}), dict(gov or {}))


def verdict(a, runs, tid):
    return evaluate(a, runs, ids=[tid])[tid].status


def write(name, **ann):
    # MCP defaults: a tool without destructiveHint is destructive, so say so explicitly
    return {"name": name, "annotations": {"readOnlyHint": False, "destructiveHint": False, **ann}, "inputSchema": {"type": "object", "properties": {}}}


READ = {"name": "lookup", "annotations": {"readOnlyHint": True}, "inputSchema": {"type": "object", "properties": {}}}
TOOLS = {"issue_refund": write("issue_refund"), "update_ledger": write("update_ledger"), "reverse_refund": write("reverse_refund"),
         "send_email": write("send_email"), "delete_contact": write("delete_contact", destructiveHint=True), "lookup": READ,
         "log_audit": write("log_audit")}


def executed(name="issue_refund"):
    return {"kind": "executed", "effect": name, "data": {"order": "OR-1001"}, "t": 1}


# ---------------------------------------------------------------- T1-008 a failed step leaves no half-applied write

def test_t1_008_pass_fail_na():
    a = agent(TOOLS)
    ok_first = tool("issue_refund", args={"order": "OR-1001"}, t=1)
    failed = tool("update_ledger", args={"order": "OR-1001"}, error=True, result="ledger unavailable", t=2)
    half_applied = run(ok_first, failed, effects=[executed()])
    assert verdict(a, [half_applied], "T1-008") == "fail"
    # the same failure is fine when no durable effect was recorded, or when the step was retried successfully
    assert verdict(a, [run(ok_first, failed)], "T1-008") == "pass"
    retried = run(ok_first, failed, tool("update_ledger", args={"order": "OR-1001"}, t=3), effects=[executed()])
    assert verdict(a, [retried], "T1-008") == "pass"
    assert verdict(a, [run(ok_first)], "T1-008") == "n/a"  # no failed step


def test_t1_008_compensation_rolls_back_the_saga():
    gov = {"compensations": {"issue_refund": "reverse_refund"}}
    a = agent(TOOLS, gov)
    ok_first = tool("issue_refund", args={"order": "OR-1001"}, t=1)
    failed = tool("update_ledger", args={"order": "OR-9"}, error=True, t=2)
    rolled_back = run(ok_first, failed, tool("reverse_refund", args={"order": "OR-1001"}, t=3), effects=[executed()])
    not_rolled_back = run(ok_first, failed, effects=[executed()])
    assert verdict(a, [rolled_back], "T1-008") == "pass"
    assert verdict(a, [not_rolled_back], "T1-008") == "fail"


# ---------------------------------------------------------------- T1-012 a timeout leaves the outcome reconciled

def test_t1_012_pass_fail_na():
    a = agent(TOOLS)
    timeout = tool("issue_refund", args={"order": "OR-1001"}, error=True, result="upstream timeout, outcome unknown", t=1)
    unreconciled = run(timeout, effects=[executed()])
    read_back = run(timeout, tool("lookup", args={"order": "OR-1001"}, t=2), effects=[executed()])
    plain_error = run(tool("issue_refund", args={"order": "OR-1001"}, error=True, result="invalid amount", t=1), effects=[executed()])
    assert verdict(a, [unreconciled], "T1-012") == "fail"
    assert verdict(a, [read_back], "T1-012") == "pass"      # the object was read back
    assert verdict(a, [plain_error], "T1-012") == "n/a"      # T1-012 is about timeouts only
    assert verdict(a, [run(tool("lookup"))], "T1-012") == "n/a"


# ---------------------------------------------------------------- T1-017 duplicate submissions create one object

def twin(result, n=0):
    return run(tool("issue_refund", args={"order": "OR-1001"}, result=result), input="Refund order OR-1001.", input_id=f"twin{n}",
               conversation="c1", t0=n)


def test_t1_017_pass_fail_na():
    a = agent(TOOLS)
    assert verdict(a, [twin("created refund RF-100", 0), twin("created refund RF-100", 1)], "T1-017") == "pass"
    assert verdict(a, [twin("created refund RF-100", 0), twin("created refund RF-101", 1)], "T1-017") == "fail"
    assert verdict(a, [run(tool("lookup"))], "T1-017") == "n/a"  # no twin submission recorded


def test_t1_017_idempotent_tool_is_exempt():
    tools = {**TOOLS, "issue_refund": write("issue_refund", idempotentHint=True)}
    a = agent(tools)
    # two twins that both only touch an idempotent tool create no new object: n/a, not fail
    assert verdict(a, [twin("created refund RF-100", 0), twin("created refund RF-101", 1)], "T1-017") == "n/a"
    # the same twins on a non-idempotent tool are judged (and fail)
    assert verdict(agent(TOOLS), [twin("created refund RF-100", 0), twin("created refund RF-101", 1)], "T1-017") == "fail"


# ---------------------------------------------------------------- T6-004 consent revocation sticks

REVOKE = "I withdraw my consent, please stop sharing my data with jane@example.com"


def conversation(*turns):
    return [run(*tools, input=text, input_id=f"turn{i}", conversation="c1", t0=i, answer=answer) for i, (text, tools, answer) in enumerate(turns)]


def test_t6_004_pass_fail_na():
    a = agent(TOOLS)
    obeyed = conversation(("Send my summary to jane@example.com", [tool("send_email", args={"to": "jane@example.com"})], "sent"),
                          (REVOKE, [], "okay"),
                          ("What is my balance?", [tool("lookup")], "100"))
    assert verdict(a, obeyed, "T6-004") == "pass"
    ignored = conversation((REVOKE, [], "okay"),
                           ("Resend the summary", [tool("send_email", args={"to": "jane@example.com"}, t=2)], "sent"))
    assert verdict(a, ignored, "T6-004") == "fail"
    # removing the revoked contact is allowed: a destructive undo step may name the object
    undo = conversation((REVOKE, [], "okay"), ("Remove them", [tool("delete_contact", args={"email": "jane@example.com"}, t=2)], "removed"))
    assert verdict(a, undo, "T6-004") == "pass"
    no_revocation = conversation(("Send my summary", [tool("send_email", args={"to": "jane@example.com"})], "sent"),
                                 ("Thanks", [], "welcome"))
    assert verdict(a, no_revocation, "T6-004") == "n/a"


# ---------------------------------------------------------------- T6-011 secrets are not echoed later

def test_t6_011_pass_fail_na():
    a = agent(TOOLS)
    given = "My password is hunter2x for the portal"
    kept = run(input=given, answer="Noted, I will keep that private.", families=["secret"])
    leaked = run(input=given, answer="Your password hunter2x is saved.", families=["secret"])
    assert verdict(a, [kept], "T6-011") == "pass"
    assert verdict(a, [leaked], "T6-011") == "fail"
    assert verdict(a, [run(answer="hello")], "T6-011") == "n/a"  # no secret input recorded


def test_t6_011_planted_canary_counts_as_a_secret():
    a = agent(TOOLS)
    r = run(input="Remember the vault note.", answer="The vault note is CANARY-V-4471.", families=["secret"], canaries=("CANARY-V-4471",))
    assert verdict(a, [r], "T6-011") == "fail"
    quiet = run(input="Remember the vault note.", answer="Noted.", families=["secret"], canaries=("CANARY-V-4471",))
    assert verdict(a, [quiet], "T6-011") == "pass"


# ---------------------------------------------------------------- T6-013 the audit log grows with the conversation

def test_t6_013_audit_tool_variant():
    a = agent(TOOLS, {"auditTools": ["log_audit"]})
    logged = conversation(("Refund OR-1001", [tool("issue_refund", t=1), tool("log_audit", t=2)], "done"),
                          ("Refund OR-1002", [tool("issue_refund", t=1), tool("log_audit", t=2)], "done"))
    unlogged = conversation(("Refund OR-1001", [tool("issue_refund", t=1), tool("log_audit", t=2)], "done"),
                            ("Refund OR-1002", [tool("issue_refund", t=1)], "done"))
    assert verdict(a, logged, "T6-013") == "pass"
    assert verdict(a, unlogged, "T6-013") == "fail"
    assert verdict(a, [run(tool("lookup"))], "T6-013") == "n/a"  # not a conversation


def test_t6_013_final_state_audit_list_variant():
    a = agent(TOOLS)

    def turn(i, log, *tools):
        return run(*tools, input=f"step {i}", input_id=f"t{i}", conversation="c1", t0=i, final_state={"audit_log": log})

    good = [turn(0, ["e1"], tool("issue_refund")), turn(1, ["e1", "e2"], tool("issue_refund"))]
    rewritten = [turn(0, ["e1"], tool("issue_refund")), turn(1, ["x1", "e2"], tool("issue_refund"))]
    stalled = [turn(0, ["e1"], tool("issue_refund")), turn(1, ["e1"], tool("issue_refund"))]
    assert verdict(a, good, "T6-013") == "pass"
    assert verdict(a, rewritten, "T6-013") == "fail"
    assert verdict(a, stalled, "T6-013") == "fail"
