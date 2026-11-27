"""Keep examples/regression_suite/ valid and runnable against the bundled refill_bot agent."""

from __future__ import annotations

from pathlib import Path

from agentest.cli import main
from agentest.standards import ext

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "examples" / "regression_suite" / "regression.yaml"
AGENTS = ROOT / "examples" / "agnostic_demo" / "agents"
IDS = "T1-018,T2-001,T2-005,T4-009,T7-014"


def test_regression_suite_example_passes_refill_bot_and_catches_buggy():
    data = ext.read_config(CFG)
    assert data["disable"] == []
    assert data["thresholds"]["steps"] == 12
    assert main(["std", "run", "--agents", str(AGENTS), "--agent", "refill_bot", "--config", str(CFG), "--ids", IDS, "--strict"]) == 0
    assert main(["std", "run", "--agents", str(AGENTS), "--agent", "refill_bot_buggy", "--config", str(CFG), "--ids", IDS, "--strict"]) == 1
