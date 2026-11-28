"""T5-001 and T5-018 do not treat a framework output / structured-result tool as undeclared.

A genuinely undeclared tool still fails, and a user tool that only shares the default output-tool name
fails when it is not in the output role. Fixtures: ``tests/fixtures/framework_output_tools``.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

import agentest
from agentest.standards.framework_output import FRAMEWORK_OUTPUT_KIND, is_framework_output_tool
from agentest.standards.metadata import Agent
from agentest.standards.otel import Run, ToolSpan, from_otlp
from agentest.standards.rules import evaluate

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "tests" / "fixtures" / "framework_output_tools"
CARD, TOOLS = PACK / "agent-card.json", PACK / "tools.json"
FIXTURES = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))["fixtures"]
CHECKS = ("T5-001", "T5-018")


def _load_build():
    spec = importlib.util.spec_from_file_location("framework_output_build", PACK / "build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    return build


def test_builder_output_matches_committed_files():
    assert _load_build().main(["--check"]) == 0, "run: PYTHONPATH=src python tests/fixtures/framework_output_tools/build.py"


def test_fixture_groups_cover_fail_pass_and_guards():
    groups = {f["group"] for f in FIXTURES}
    assert {"must-fail", "must-pass"} <= groups
    assert {f["expect"] for f in FIXTURES if f["group"] == "must-fail"} == {"fail"}
    assert {f["expect"] for f in FIXTURES if f["group"] in ("must-pass",)} == {"pass"}


@pytest.mark.parametrize("tid", CHECKS)
@pytest.mark.parametrize("fixture", FIXTURES, ids=[f["id"] for f in FIXTURES])
def test_undeclared_tool_verdict(fixture, tid):
    result = agentest.run(PACK / fixture["file"], card=CARD, tools=TOOLS, ids=[tid]).checks[0]
    assert result.status == fixture["expect"]
    if fixture["expect"] == "fail":
        for name in fixture["undeclared"]:
            assert name in result.detail
        if fixture["id"] == "F01":
            assert "final_result" not in result.detail
        if fixture["id"] == "F02":
            assert "lookup_account" not in result.detail


def test_marked_tool_is_skipped_by_the_rule_without_ingest():
    """The check reads only the mark, so an in-memory span with the kind set is enough."""
    card = {"name": "unit", "skills": [], "capabilities": {"extensions": []}}
    tools = {"lookup": {"name": "lookup", "annotations": {"readOnlyHint": True}, "inputSchema": {"type": "object", "properties": {}}}}
    agent = Agent("unit", Path("/nonexistent"), card, tools, {})
    marked = ToolSpan("final_result", {"ok": True}, "done", False, "", 1, attrs={"agentest.tool.kind": FRAMEWORK_OUTPUT_KIND})
    undeclared = ToolSpan("secret_wire", {}, "sent", False, "", 2)
    run = Run("u1", 0, "look up", "done", tools=[marked, undeclared])
    assert is_framework_output_tool(marked) and not is_framework_output_tool(undeclared)
    ev = evaluate(agent, [run], ids=["T5-001", "T5-018"])
    assert ev["T5-001"].status == ev["T5-018"].status == "fail"
    assert ev["T5-001"].detail == "undeclared tools: ['secret_wire']"


def test_ingest_stamps_the_mark_from_the_output_role():
    build = _load_build()
    cases = {c["id"]: c for c in build.CASES}
    doc = build.trace_doc(cases["P02"], 2)
    run = from_otlp(doc)
    names = [t.name for t in run.tools]
    assert "final_result" in names and "lookup_account" in names
    out = next(t for t in run.tools if t.name == "final_result")
    assert out.attrs.get("agentest.tool.kind") == FRAMEWORK_OUTPUT_KIND
    user = next(t for t in from_otlp(build.trace_doc(cases["F02"], 8)).tools if t.name == "final_result")
    assert user.attrs.get("agentest.tool.kind") != FRAMEWORK_OUTPUT_KIND
    assert user.result == "card blocked for account A-12"
