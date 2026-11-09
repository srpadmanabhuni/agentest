"""Registry hook and the shared primitives (object ledger, state diff, turn index, write class)."""
from __future__ import annotations

from pathlib import Path

from agentest.standards.detectors._core import (
    Detector,
    classify_write,
    object_ledger,
    state_diff,
    turn_index,
)
from agentest.standards.detectors.registry import get, register
from agentest.standards.expr import R
from agentest.standards.metadata import Agent
from agentest.standards.otel import Run, ToolSpan
from agentest.standards.rules import Ctx, evaluate


def _agent() -> Agent:
    tools = {
        "lookup_alpha": {
            "name": "lookup_alpha",
            "description": "Read a record by id",
            "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}},
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
        },
        "mutate_alpha": {
            "name": "mutate_alpha",
            "description": "Record a decision",
            "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}},
            "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False},
        },
    }
    card = {"name": "unit", "skills": [{"id": "s", "examples": ["Handle the request."]}], "capabilities": {}}
    return Agent("unit", Path("/tmp/det-unit"), card, tools, {})


def _run(**kw) -> Run:
    base = dict(input_id="task", rep=0, input="Handle the request.", answer="Noted.", tools=[])
    base.update(kw)
    return Run(**base)


def test_register_replaces_and_applies_reason_is_not_applicable():
    """A later register() for the same test id wins. applies() reason is n/a and evaluate() is not called."""
    orig = get("T1-007")
    assert isinstance(orig, Detector)

    class Takeover(Detector):
        test_id = "T1-007"
        what = "hook takeover"

        def applies(self, ctx):
            return "synthetic signal absent"

        def evaluate(self, ctx):
            raise AssertionError("evaluate must not run when applies returns a reason")

        def evidence(self):
            return []

    agent = _agent()
    runs = [_run()]
    try:
        register(Takeover())
        assert get("T1-007") is not orig
        verdict = evaluate(agent, runs, ["T1-007"])["T1-007"]
        assert verdict.status == "n/a" and "synthetic signal absent" in verdict.detail
        kept = get("T1-007")
        register(Takeover(), replace=False)
        assert get("T1-007") is kept
    finally:
        register(orig)
    assert get("T1-007") is orig
    assert isinstance(evaluate(agent, runs, ["T1-007"])["T1-007"], R)


def test_object_ledger_state_diff_turn_index_and_write_class():
    agent = _agent()
    read = ToolSpan(name="lookup_alpha", args={"id": "REC-1"}, result="{}", error=False, actor="", t=1)
    write = ToolSpan(name="mutate_alpha", args={"id": "REC-1"}, result="{}", error=False, actor="", t=2)
    first = _run(input_id="turn-a", tools=[read], conversation="C", t0=1, effects=[
        {"kind": "executed", "effect": "record", "data": {"object": "REC-1", "effect_id": "e1"}}])
    second = _run(input_id="turn-b", tools=[write], conversation="C", t0=2)
    ctx = Ctx(agent, [second, first], "examples")
    assert object_ledger(first) == [("record", "REC-1", "e1")]
    assert state_diff({"case": {"status": "open"}}, {"case": {"status": "done"}, "extra": 1}) == {"case.status", "extra"}
    turns = turn_index(ctx)
    assert len(turns) == 1 and [r.input_id for r in turns[0]] == ["turn-a", "turn-b"]
    assert classify_write(ctx, read) == "read"
    assert classify_write(ctx, write) == "destructive"
