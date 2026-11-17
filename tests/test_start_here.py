"""docs/START_HERE.md stays true: its commands run from the repo root and print the output it pastes."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs/START_HERE.md").read_text(encoding="utf-8")


def _run(*args: str) -> str:
    p = subprocess.run([sys.executable, "-m", "agentest", "std", "run", *args], cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert p.returncode == 0, p.stderr[-2000:]
    return p.stdout


def _pasted_lines(output_start: str) -> list[str]:
    """Lines of the first ```text block that starts with ``output_start``."""
    for block in re.findall(r"^```text\n(.*?)^```", DOC, re.S | re.M):
        if block.startswith(output_start):
            return [line for line in block.splitlines() if line.strip()]
    raise AssertionError(output_start)


def test_demo_output_matches_the_page():
    out = _run("--agents", "examples/agnostic_demo/agents", "--agent", "refill_bot_buggy",
               "--ids", "T1-018,T2-001,T4-003,T7-014", "--format", "md")
    for line in _pasted_lines("# agentest")[1:]:  # skip the version header, which changes per release
        assert line in out, line


def test_clean_sibling_output_matches_the_page():
    out = _run("--agents", "examples/agnostic_demo/agents", "--agent", "refill_bot")
    for line in _pasted_lines("refill_bot: 55 pass"):
        assert line in out, line


def test_tiny_example_trace_fails_the_success_claim_checks():
    out = _run("--otlp", "examples/start_here/claims-success.otlp.json", "--ids", "T1-005,T1-018", "--format", "md")
    for line in _pasted_lines("| ID | status | detail |")[2:]:
        assert line in out, line
