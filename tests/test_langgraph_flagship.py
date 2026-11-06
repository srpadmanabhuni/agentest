"""LangGraph flagship example: docs, import dialect stability, and offline demo script."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples" / "langgraph_import"
SCRIPT = EX / "test_langgraph.py"
DOC = ROOT / "docs" / "integrations" / "langgraph.md"


def test_flagship_paths_exist():
    assert SCRIPT.is_file()
    assert DOC.is_file()
    assert (EX / "README.md").is_file()
    assert (EX / "native" / "expense_bot.jsonl").is_file()
    assert (EX / "import" / "map.json").is_file()
    assert (EX / "agents" / "expense_bot" / "agent-card.json").is_file()
    assert (EX / "agents" / "expense_bot" / "tools.json").is_file()
    assert (EX / "agents" / "expense_bot" / "traces" / "expense_bot.otlp.jsonl").is_file()


def test_docs_link_flagship_and_avoid_other_framework_templates():
    text = DOC.read_text(encoding="utf-8")
    assert "langgraph_msgs" in text
    assert "examples/langgraph_import" in text
    assert "Bring an agent trace, contribute a test" in text
    # Flagship only — no second framework template folder advertised here.
    low = text.lower()
    assert "crewai" not in low
    assert "examples/smolagents" not in low
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/integrations/langgraph.md" in readme
    assert "examples/langgraph_import/test_langgraph.py" in readme


def test_flagship_script_runs_offline():
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT / "src")}
    env.pop("AGENTEST_HUB_CATALOGUE", None)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        env=env,
    )
    assert proc.returncode == 0, (proc.stdout[-2000:], proc.stderr[-2000:])
    out = proc.stdout
    assert "LangGraph flagship example" in out
    assert "| T1-001 | pass |" in out
    assert "Bring an agent trace, contribute a test" in out
    # Do not treat this demo as a published scoreboard.
    assert "scoreboard" in out.lower() or "illustrative" in out.lower()
