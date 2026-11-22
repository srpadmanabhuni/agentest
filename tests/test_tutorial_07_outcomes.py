"""Tutorial 7 (writing expected outcomes) stays true: real validate/run output on refill_bot demos."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDS = "T1-001,T1-002,T1-018"
DOC = (ROOT / "docs/tutorials/07-writing-expected-outcomes.md").read_text(encoding="utf-8")
ENV = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""))
INSPECT = r"""
from pathlib import Path
import json
from agentest.standards import metadata, runner

agent = metadata.load_all(Path("examples/agnostic_demo/agents"))["refill_bot_buggy"]
for run in runner.runs(agent):
    if run.input_id in {"canon", "social"} and run.rep == 0:
        print(run.input_id, run.input)
        print("  answer:", run.answer)
        print("  output:", json.dumps(run.final_state.get("output"), default=str))
"""


def run(*argv, check=True):
    p = subprocess.run(list(argv), cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=300)
    if check:
        assert p.returncode == 0, (argv, p.stdout[-1500:], p.stderr[-1500:])
    return p.stdout


def rows(out):
    return [ln.strip() for ln in out.splitlines() if ln.startswith("| T")]


def test_validate_matches_the_tutorial():
    out = run("agentest", "std", "validate", "--agents", "examples/agnostic_demo/agents", "--agent", "refill_bot")
    assert "1/1 agents have valid AgentCard + MCP tools metadata" in out
    assert "1/1 agents have valid AgentCard + MCP tools metadata" in DOC


def test_refill_bot_passes_as_the_tutorial_shows():
    out = run("agentest", "std", "run", "--agents", "examples/agnostic_demo/agents",
              "--agent", "refill_bot", "--ids", IDS, "--format", "md")
    assert "3 pass, 0 fail, 0 n/a" in out
    assert "3 pass, 0 fail, 0 n/a over 1 agent(s)." in DOC
    for r in rows(out):
        assert r in DOC, r


def test_refill_bot_buggy_fails_social_as_the_tutorial_shows():
    out = run("agentest", "std", "run", "--agents", "examples/agnostic_demo/agents",
              "--agent", "refill_bot_buggy", "--ids", IDS, "--format", "md")
    assert "1 pass, 2 fail, 0 n/a" in out
    assert "1 pass, 2 fail, 0 n/a over 1 agent(s)." in DOC
    for r in rows(out):
        assert r in DOC, r


def test_inspect_output_matches_the_tutorial():
    out = run(sys.executable, "-c", INSPECT)
    assert out.strip() in DOC


def test_strict_mode_matches_the_tutorial():
    out = run("agentest", "std", "run", "--agents", "examples/agnostic_demo/agents",
              "--agent", "refill_bot_buggy", "--ids", IDS, "--mode", "strict", "--format", "md")
    assert "1 pass, 0 fail, 2 n/a" in out
    assert "1 pass, 0 fail, 2 n/a over 1 agent(s)." in DOC
    for r in rows(out):
        assert r in DOC, r
