"""Tutorial 6 (personal data and secret leaks) stays true: four fails on eager, four passes after the simulated fix."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDS = "T5-004,T4-009,T6-011,T7-014"
DOC = (ROOT / "docs/tutorials/06-personal-data-leaks.md").read_text(encoding="utf-8")
ENV = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""))


def run(*argv):
    p = subprocess.run(list(argv), cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=300)
    assert p.returncode == 0, (argv, p.stdout[-1500:], p.stderr[-1500:])
    return p.stdout


def rows(out):
    return [ln.strip() for ln in out.splitlines() if ln.startswith("| T")]


def test_eager_fails_all_four_as_the_tutorial_shows():
    out = run("agentest", "std", "run", "--agents", "agents", "--agent", "eager", "--ids", IDS, "--format", "md")
    assert "0 pass, 4 fail, 0 n/a" in out
    for r in rows(out):
        assert r in DOC, r


def test_show_matches_the_tutorial():
    out = run(sys.executable, "docs/tutorials/make_fixed_traces.py", "--show", "--ids", IDS)
    assert out.strip() in DOC


def test_simulated_fix_passes_all_four(tmp_path):
    fixed = tmp_path / "eager-fixed.jsonl"
    run(sys.executable, "docs/tutorials/make_fixed_traces.py", "--out", str(fixed), "--ids", IDS, "--fixed")
    out = run("agentest", "std", "run", "--otlp", str(fixed), "--card", "agents/eager/agent-card.json",
              "--tools", "agents/eager/tools.json", "--ids", IDS, "--format", "md")
    assert "4 pass, 0 fail, 0 n/a" in out
    for r in rows(out):
        assert r in DOC, r
