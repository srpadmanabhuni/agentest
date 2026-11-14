"""pytest template: check recorded LangGraph message-list episodes with agentest.

Copy this file into your own repository's tests/ folder and point it at your files
with environment variables (or edit the defaults below). Offline: no LangGraph
package, no model, no network. Needs only agentest (runtime dependency: PyYAML).

  AGENTEST_LG_NATIVE   your recorded episodes, one JSON message list per line (.jsonl)
  AGENTEST_LG_MAP      import map (dialect langgraph_msgs; see the example map.json)
  AGENTEST_LG_TOOLS    MCP-style tools.json declaring each tool and its annotations
  AGENTEST_LG_CARD     A2A-style agent-card.json
  AGENTEST_LG_SERVICE  service name written into the imported traces
  AGENTEST_LG_MUST_PASS  comma-separated check IDs that must report "pass"

The defaults point at the synthetic example in examples/langgraph_import/ so the
template runs as-is from a clone of this repository:

  python -m pytest -q templates/test_langgraph.py

Guide: docs/integrations/langgraph.md
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

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


def _agentest(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "agentest", *argv], text=True, capture_output=True)


@pytest.fixture(scope="module")
def report(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict]:
    for path in (NATIVE, MAP, TOOLS, CARD):
        assert path.is_file(), f"missing input file: {path}"
    out = tmp_path_factory.mktemp("agentest-langgraph")
    otlp = out / "traces.otlp.jsonl"
    imp = _agentest("std", "import", str(NATIVE), "--map", str(MAP), "--tools", str(TOOLS), "--service", SERVICE, "--out", str(otlp))
    assert imp.returncode == 0, imp.stderr or imp.stdout
    assert otlp.is_file() and otlp.stat().st_size > 0, "import wrote no OTLP traces"

    result = out / "report.json"
    run = _agentest("std", "run", "--otlp", str(otlp), "--card", str(CARD), "--tools", str(TOOLS), "--json", str(result))
    assert run.returncode == 0, run.stderr or run.stdout
    data = json.loads(result.read_text(encoding="utf-8"))
    assert len(data) == 1, f"expected one agent in the report, got {sorted(data)}"
    return next(iter(data.values()))


def test_every_check_reports_a_status(report: dict[str, dict]) -> None:
    bad = {tid: cell.get("status") for tid, cell in report.items() if cell.get("status") not in STATUSES}
    assert not bad, f"unexpected statuses: {bad}"


@pytest.mark.parametrize("test_id", MUST_PASS)
def test_required_check_passes(report: dict[str, dict], test_id: str) -> None:
    cell = report.get(test_id)
    assert cell is not None, f"{test_id} not in the report"
    assert cell["status"] == "pass", f"{test_id}: {cell['status']} — {cell.get('detail')}"
