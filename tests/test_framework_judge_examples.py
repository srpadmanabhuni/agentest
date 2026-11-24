"""The framework 'export a run and judge it' examples run offline and catch the skipped lookup."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ["langgraph", "openai_agents", "pydantic_ai"]


def _run(name, *args):
    script = ROOT / "examples" / "frameworks" / name / "judge.py"
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, cwd=ROOT, timeout=120)


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_catches_refund_before_lookup(name):
    out = _run(name)
    assert out.returncode == 0, out.stderr
    assert "0 pass, 3 fail (T2-001, T2-002, T2-013)" in out.stdout
    assert "issue_refund before ['lookup_order']" in out.stdout


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_strict_exits_1(name):
    assert _run(name, "--strict").returncode == 1


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_stays_short(name):
    lines = (ROOT / "examples" / "frameworks" / name / "judge.py").read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 35
