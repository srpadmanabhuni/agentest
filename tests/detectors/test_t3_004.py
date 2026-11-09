"""Detector T3-004: registration, applicability, and a verdict on a synthetic run."""
from __future__ import annotations

from pathlib import Path

from agentest.standards.detectors.registry import get
from agentest.standards.metadata import Agent
from agentest.standards.otel import Run, ToolSpan
from agentest.standards.rules import Ctx, evaluate

TID = "T3-004"


def _agent() -> Agent:
    tools = {
        "lookup_alpha": {
            "name": "lookup_alpha",
            "description": "Read a record by id",
            "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
        },
        "mutate_alpha": {
            "name": "mutate_alpha",
            "description": "Record a decision",
            "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "decision": {"type": "string"}}, "required": ["id"]},
            "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
        },
    }
    card = {"name": "unit", "skills": [{"id": "s", "examples": ["Handle the request."]}], "capabilities": {}}
    return Agent("unit", Path("/tmp/det-unit"), card, tools, {})


def _runs():
    span = ToolSpan(name="lookup_alpha", args={"id": "REC-1"}, result='{"status": "open"}', error=False, actor="", t=1)
    return [Run(input_id="task", rep=0, input="Handle the request.", answer="Noted.", tools=[span])]


def test_registered_detector():
    det = get(TID)
    assert det is not None
    assert det.test_id == TID and det.what
    assert callable(det.applies) and callable(det.evaluate) and callable(det.evidence)


def test_synthetic_verdict_and_evidence():
    det = get(TID)
    agent, runs = _agent(), _runs()
    why = det.applies(Ctx(agent, runs, "examples"))
    assert why is None or isinstance(why, str)
    verdict = evaluate(agent, runs, [TID])[TID]
    assert verdict.status in {"pass", "fail", "n/a", "not-assessed"}
    assert isinstance(det.evidence(), list)
