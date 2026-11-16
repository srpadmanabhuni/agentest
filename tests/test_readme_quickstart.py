"""The README "Try it" quickstart stays true.

The README promises that its three-line source quickstart reproduces the demo clip and prints one
T1-018 fail row on the recorded shopping agent a22. This test runs the agentest line from that bash
block (the clone and venv lines are skipped; CI already runs from an installed checkout) and checks
the README's own "Expected:" row against the real output.
"""
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
TRY_IT = README.split("## Try it", 1)[1].split("\n## ", 1)[0]


def _quickstart_command():
    block = re.search(r"```bash\n(.*?)```", TRY_IT, re.S)
    assert block, "README Try it section has no bash block"
    lines = [ln.strip() for ln in block.group(1).splitlines() if ln.strip().startswith("agentest ")]
    assert len(lines) == 1, lines
    return shlex.split(lines[0])


def _expected_row():
    m = re.search(r"Expected: one row, `([^`]+)`", TRY_IT)
    assert m, "README Try it section lost its Expected: line"
    return [c.strip() for c in m.group(1).split("|")]


def test_quickstart_is_three_lines_from_source():
    block = re.search(r"```bash\n(.*?)```", TRY_IT, re.S).group(1)
    lines = [ln for ln in block.splitlines() if ln.strip()]
    assert len(lines) == 3, lines
    assert lines[0].startswith("git clone") and "pip install" in lines[1]


def test_quickstart_prints_the_expected_row():
    argv = _quickstart_command()
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""))
    p = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert p.returncode == 0, (p.stdout[-1500:], p.stderr[-1500:])
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")]
            for ln in p.stdout.splitlines() if ln.startswith("| T")]
    assert rows == [_expected_row()], p.stdout[-1500:]
