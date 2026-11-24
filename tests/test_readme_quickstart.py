"""The clone quickstart (moved from the README to docs/INSTALL-AND-QUICKSTART.md) stays true.

The page promises that its three-line source quickstart reproduces the demo clip and prints one
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
README = (ROOT / "docs" / "INSTALL-AND-QUICKSTART.md").read_text(encoding="utf-8")
TRY_IT = README.split("## Clone quickstart: the shopping agent a22", 1)[1].split("\n## ", 1)[0]


def _from_source_block():
    """The bash block that clones the repo and runs the a22 demo (not the pip-install block)."""
    for block in re.finditer(r"```bash\n(.*?)```", TRY_IT, re.S):
        body = block.group(1)
        if "git clone" in body and "agentest std run --agent a22" in body:
            return body
    raise AssertionError("clone quickstart section has no from-source bash block for a22")


def _quickstart_command():
    lines = [ln.strip() for ln in _from_source_block().splitlines() if ln.strip().startswith("agentest ")]
    assert len(lines) == 1, lines
    return shlex.split(lines[0])


def _expected_row():
    m = re.search(r"Expected: one row, `([^`]+)`", TRY_IT)
    assert m, "clone quickstart section lost its Expected: line"
    return [c.strip() for c in m.group(1).split("|")]


def test_quickstart_is_three_lines_from_source():
    lines = [ln for ln in _from_source_block().splitlines() if ln.strip()]
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
