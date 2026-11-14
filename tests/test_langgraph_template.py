"""The LangGraph pytest template in templates/ runs green against the bundled synthetic example."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "test_langgraph.py"


def test_langgraph_template_runs_on_example() -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("AGENTEST_LG_")}
    env.pop("AGENTEST_HUB_CATALOGUE", None)
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(TEMPLATE)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "3 passed" in proc.stdout, proc.stdout
