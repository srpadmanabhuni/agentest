"""A roll-up span (a summary of tool calls that already have spans of their own) is not a tool call.

Some instrumentations add one more ``execute_tool`` span after parallel calls, with a placeholder tool name and no
arguments. Before, T5-001 and T5-018 reported it as an undeclared tool and T1-007 as a state-changing call. The reader now
sets it aside (``Run.rollups``): the marker attribute or a placeholder name from ``semconv.yaml`` with no real arguments
makes a span a roll-up. A real undeclared tool, and a real call that merely shares the placeholder name, still fail.
Fixtures: ``tests/fixtures/rollup_spans`` (built by its ``build.py``; the manifest holds the expected verdicts).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

import agentest
from agentest.standards import otel

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "tests" / "fixtures" / "rollup_spans"
CARD, TOOLS = PACK / "agent-card.json", PACK / "tools.json"
MANIFEST = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
FIXTURES = MANIFEST["fixtures"]
CHECKS = MANIFEST["checks"]


def _verdicts(fixture) -> dict[str, str]:
    r = agentest.run(PACK / fixture["file"], card=CARD, tools=TOOLS, ids=CHECKS)
    return {c.id: c.status for c in r.checks}


def _run(fixture) -> otel.Run:
    return otel.from_otlp(otel.read_otlp_file(PACK / fixture["file"])[0])


def test_builder_output_matches_committed_files():
    spec = importlib.util.spec_from_file_location("rollup_build", PACK / "build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    assert build.main(["--check"]) == 0, "run: python tests/fixtures/rollup_spans/build.py"


def test_fixture_groups_cover_rollup_control_undeclared_and_empty_input():
    assert {f["group"] for f in FIXTURES} == {"rollup", "control", "undeclared", "empty-input"}


@pytest.mark.parametrize("fixture", FIXTURES, ids=[f["id"] for f in FIXTURES])
def test_verdicts(fixture):
    assert _verdicts(fixture) == fixture["expect"]


@pytest.mark.parametrize("fixture", FIXTURES, ids=[f["id"] for f in FIXTURES])
def test_rollup_spans_are_set_aside_and_not_counted_as_calls(fixture):
    run = _run(fixture)
    assert len(run.rollups) == fixture["rollups"]
    assert not any(t.name == "(merged tools)" and not t.args for t in run.tools)
    # the span is no tool call and no step either: tool-call counts and span-based checks never see it
    assert all(r["id"] not in {s["id"] for s in run.spans} for r in run.rollups)


def test_a_rollup_changes_nothing_else_in_the_verdicts():
    """Judged with and without the roll-up span, a run gets the same verdict on every default check."""
    by = {f["id"]: f for f in FIXTURES}
    with_rollup = agentest.run(PACK / by["R01"]["file"], card=CARD, tools=TOOLS).checks
    without = agentest.run(PACK / by["R04"]["file"], card=CARD, tools=TOOLS).checks
    assert {c.id: c.status for c in with_rollup} == {c.id: c.status for c in without}


def test_undeclared_tool_is_named_and_the_rollup_is_not():
    by = {f["id"]: f for f in FIXTURES}
    detail = {c.id: c.detail for c in agentest.run(PACK / by["U01"]["file"], card=CARD, tools=TOOLS, ids=["T5-001"]).checks}["T5-001"]
    assert "wipe_calendar" in detail and "(merged tools)" not in detail


def test_a_call_that_shares_the_placeholder_name_but_has_arguments_is_still_named():
    by = {f["id"]: f for f in FIXTURES}
    detail = {c.id: c.detail for c in agentest.run(PACK / by["U02"]["file"], card=CARD, tools=TOOLS, ids=["T5-001"]).checks}["T5-001"]
    assert "(merged tools)" in detail


@pytest.mark.parametrize("attrs, expect", [
    ({"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "(merged tools)"}, True),
    ({"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "(merged tools)", "gen_ai.tool.call.arguments": "N/A"}, True),
    ({"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "(merged tools)", "gen_ai.tool.call.arguments": '{"a": 1}'}, False),
    ({"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "lookup"}, False),
    ({"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "lookup", "agentest.span.rollup": True}, True),
    ({"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "(merged tools)", "agentest.span.rollup": False}, False),
    ({"gen_ai.operation.name": "chat", "agentest.span.rollup": True}, False),
])
def test_is_rollup(attrs, expect):
    assert otel.is_rollup(attrs) is expect
