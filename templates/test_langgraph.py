"""pytest template: check recorded LangGraph message-list episodes with agentest.

Copy this file into your own repository's tests/ folder and point it at your files
with environment variables (or edit the defaults below). Offline: no LangGraph
package, no model, no network. Needs agentest (runtime dependency: PyYAML).

  AGENTEST_LG_NATIVE   your recorded episodes, one JSON message list per line (.jsonl)
  AGENTEST_LG_MAP      import map (dialect langgraph_msgs; see the example map.json)
  AGENTEST_LG_TOOLS    MCP-style tools.json declaring each tool and its annotations
  AGENTEST_LG_CARD     A2A-style agent-card.json
  AGENTEST_LG_SERVICE  service name written into the imported traces
  AGENTEST_LG_MUST_PASS  comma-separated check IDs that must report "pass"

The defaults point at the recorded example in examples/langgraph_import/ so the
template runs as-is from a clone of this repository:

  python -m pytest -q templates/test_langgraph.py

Guide: docs/integrations/langgraph.md
"""
# Ref: [LangGraph-docs] (message-list shape imported); importer is src/agentest/standards/importers.py.

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import agentest
from agentest.standards import importers

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "langgraph_import"

NATIVE = Path(os.environ.get("AGENTEST_LG_NATIVE", EXAMPLE / "native" / "expense_bot.jsonl"))
MAP = Path(os.environ.get("AGENTEST_LG_MAP", EXAMPLE / "import" / "map.json"))
TOOLS = Path(os.environ.get("AGENTEST_LG_TOOLS", EXAMPLE / "agents" / "expense_bot" / "tools.json"))
CARD = Path(os.environ.get("AGENTEST_LG_CARD", EXAMPLE / "agents" / "expense_bot" / "agent-card.json"))
SERVICE = os.environ.get("AGENTEST_LG_SERVICE", "expense_bot")
# Checks your agent must pass. The example list is a starting point, not a recommendation.
MUST_PASS = [t.strip() for t in os.environ.get("AGENTEST_LG_MUST_PASS", "T1-001,T5-001").split(",") if t.strip()]

STATUSES = {"pass", "fail", "n/a"}


def _import_otlp(dest: Path) -> None:
    """Native episodes -> OTLP, using the same importer as ``agentest std import``."""
    mapping = json.loads(MAP.read_text(encoding="utf-8"))
    is_write = importers.is_write_from_tools(TOOLS)
    raws = importers.read_native(NATIVE)
    service = SERVICE or (raws[0].get("agent") if raws and raws[0].get("agent") else "agent")
    try:
        docs = importers.to_docs(raws, mapping, service, is_write, base=MAP.parent)
    except importers.NativeLogError as e:
        raise AssertionError(f"import failed: {e}") from e
    text = "".join(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n" for doc in docs)
    dest.write_text(text, encoding="utf-8")


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> agentest.Result:
    for path in (NATIVE, MAP, TOOLS, CARD):
        assert path.is_file(), f"missing input file: {path}"
    out = tmp_path_factory.mktemp("agentest-langgraph")
    otlp = out / "traces.otlp.jsonl"
    _import_otlp(otlp)
    assert otlp.is_file() and otlp.stat().st_size > 0, "import wrote no OTLP traces"
    found = agentest.run(otlp, card=CARD, tools=TOOLS)
    assert len(found.verdicts) == 1, f"expected one agent in the report, got {sorted(found.verdicts)}"
    return found


def test_every_check_reports_a_status(result: agentest.Result) -> None:
    bad = {check.id: check.status for check in result.checks if check.status not in STATUSES}
    assert not bad, f"unexpected statuses: {bad}"


@pytest.mark.parametrize("test_id", MUST_PASS)
def test_required_check_passes(result: agentest.Result, test_id: str) -> None:
    agentest.assert_passes(result, test_id)
