"""--max-na N: an opt-in gate on the number of n/a checks (issue #405)."""
from pathlib import Path

from agentest.cli import main

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "examples" / "regression_suite" / "regression.yaml"
AGENTS = ROOT / "examples" / "agnostic_demo" / "agents"
BASE = ["std", "run", "--agents", str(AGENTS), "--agent", "refill_bot", "--config", str(CFG), "--ids", "T1-018,T6-004,T6-010"]


def test_default_ignores_na():
    assert main(BASE) == 0
    assert main([*BASE, "--strict"]) == 0


def test_max_na_fails_when_the_limit_is_exceeded(capsys):
    assert main([*BASE, "--max-na", "1"]) == 1
    assert "2 checks are n/a, more than --max-na 1" in capsys.readouterr().err


def test_max_na_passes_at_or_below_the_limit():
    assert main([*BASE, "--max-na", "2"]) == 0


def test_max_na_also_gates_a_piped_report(capsys):
    assert main([*BASE, "--format", "csv", "--max-na", "0"]) == 1
