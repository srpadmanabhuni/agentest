"""`agentest demo refill`: the refill example ships in the wheel, so the first FAIL needs no clone.

The packaged files are the standard agent files the judge reads for any agent (AgentCard, tools list, OTLP traces). The
command runs the same judge as ``std run``; nothing in a check refers to the example.
"""

import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from agentest.cli import build_parser, main

ROOT = Path(__file__).resolve().parents[1]
PACKED = ROOT / "src" / "agentest" / "demo_data" / "refill"
SOURCE = ROOT / "examples" / "agnostic_demo" / "agents"
AGENTS = ("refill_bot", "refill_bot_buggy")
SHIPPED = (
    "refill/refill_bot/agent-card.json",
    "refill/refill_bot/tools.json",
    "refill/refill_bot/traces/refill_bot.otlp.jsonl",
    "refill/refill_bot_buggy/agent-card.json",
    "refill/refill_bot_buggy/tools.json",
    "refill/refill_bot_buggy/traces/refill_bot_buggy.otlp.jsonl",
)


def _run(args, capsys, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    code = main(args)
    return code, capsys.readouterr()


def test_demo_takes_an_example_name():
    parser = build_parser()
    demo = next(a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction").choices["demo"]
    assert "refill" in demo.format_help()
    assert "agentest demo refill" in parser.format_help()


def test_packaged_files_equal_the_example_folder():
    for agent in AGENTS:
        packed = sorted(p.relative_to(PACKED / agent) for p in (PACKED / agent).rglob("*") if p.is_file())
        source = sorted(p.relative_to(SOURCE / agent) for p in (SOURCE / agent).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
        assert packed == source
        for rel in packed:
            assert (PACKED / agent / rel).read_bytes() == (SOURCE / agent / rel).read_bytes(), f"{agent}/{rel} differs; copy examples/agnostic_demo/agents/{agent} again"


def test_buggy_build_exits_1_with_the_t1_018_fail_line(capsys, monkeypatch):
    code, cap = _run(["demo", "refill"], capsys, monkeypatch)
    assert code == 1
    assert "bundled sample refill_bot_buggy" in cap.out
    assert re.search(r"^\s+FAIL  T1-018  .+\n\s+social#0: claims success$", cap.out, re.M)
    assert "\033[" not in cap.out
    assert "agentest demo refill --fixed" in cap.out


def test_fixed_build_passes_t1_018_and_exits_0(capsys, monkeypatch):
    code, cap = _run(["demo", "refill", "--fixed"], capsys, monkeypatch)
    assert code == 0
    assert "bundled sample refill_bot" in cap.out
    assert re.search(r"^\s+PASS  T1-018  .+\n\s+claims consistent over \d+ run\(s\)$", cap.out, re.M)
    assert " 0 failed" in cap.out
    assert "FAIL" not in cap.out


def test_demo_verdict_is_the_std_run_verdict(capsys, monkeypatch):
    """One judge: the demo and `std run --agents <folder>` agree, because nothing special-cases the example."""
    from agentest.standards import metadata, runner

    res = runner.run_all(metadata.load_all(PACKED), mode="examples")
    assert res["refill_bot_buggy"]["T1-018"].status == "fail"
    assert res["refill_bot"]["T1-018"].status == "pass"
    code, cap = _run(["demo", "refill"], capsys, monkeypatch)
    assert res["refill_bot_buggy"]["T1-018"].detail in cap.out
    assert code == (1 if any(r.status == "fail" for r in res["refill_bot_buggy"].values()) else 0)


def test_no_check_names_the_bundled_agent():
    for p in (ROOT / "src" / "agentest" / "standards").glob("*.py"):
        text = p.read_text(encoding="utf-8")
        assert "refill_bot" not in text, f"{p.name} refers to the bundled agent"


def test_html_report(tmp_path, capsys, monkeypatch):
    dest = tmp_path / "r.html"
    code, cap = _run(["demo", "refill", "--html", str(dest)], capsys, monkeypatch)
    assert code == 1
    assert f"wrote HTML report to {dest}" in cap.out
    assert "T1-018" in dest.read_text(encoding="utf-8")


def test_bad_combinations_are_usage_errors(capsys, monkeypatch):
    code, cap = _run(["demo", "refill", "--agent", "a22"], capsys, monkeypatch)
    assert code == 2 and "either an example name or --agent" in cap.err
    code, cap = _run(["demo", "--fixed"], capsys, monkeypatch)
    assert code == 2 and "--fixed needs an example name" in cap.err


def test_plain_demo_is_unchanged(capsys, monkeypatch):
    code, cap = _run(["demo"], capsys, monkeypatch)
    assert code == 0
    assert "bundled sample overreach" in cap.out
    assert "agentest demo --html report.html" in cap.out


def _doc_blocks(text: str, start: str, end: str) -> list[str]:
    section = text.split(start, 1)[1].split(end, 1)[0]
    return re.findall(r"```text\n(.*?)```", section, re.S)


def test_readme_snippets_match_the_real_output(capsys, monkeypatch):
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    fail_block, pass_block = _doc_blocks(readme, "**A second supplied example: a refill assistant", "**4. Try your own trace**")
    _, cap = _run(["demo", "refill"], capsys, monkeypatch)
    assert fail_block in cap.out
    _, cap = _run(["demo", "refill", "--fixed"], capsys, monkeypatch)
    assert pass_block in cap.out


def test_docs_name_both_commands_and_keep_public_wording():
    for rel in ("README.md", "docs/GETTING-STARTED.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "agentest demo refill" in text and "agentest demo refill --fixed" in text, rel
    cl = (ROOT / "changelog.d" / "demo-refill.md").read_text(encoding="utf-8").lower()
    assert "165 tests" in cl
    for word in ("synthetic", "fork"):
        assert word not in cl


def test_pyproject_ships_the_example():
    toml = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"agentest.demo_data" = ["refill/*/*.json", "refill/*/traces/*"]' in toml


@pytest.mark.skipif(not (os.environ.get("CI") or os.environ.get("AGENTEST_WHEEL_TESTS")), reason="builds a wheel and installs it into a fresh venv; runs in CI or with AGENTEST_WHEEL_TESTS=1")
def test_fresh_venv_from_the_built_wheel(tmp_path):
    """Build the wheel, list the example files in it, install it into an empty venv and run from an empty directory."""
    wheelhouse = tmp_path / "wheelhouse"
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "-q", "-w", str(wheelhouse), str(ROOT)], check=True, timeout=900)
    wheel = next(wheelhouse.glob("agentest_ai-*.whl"))
    names = zipfile.ZipFile(wheel).namelist()
    for rel in SHIPPED:
        assert f"agentest/demo_data/{rel}" in names, rel

    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    bindir = venv / ("Scripts" if os.name == "nt" else "bin")
    subprocess.run([str(bindir / "python"), "-m", "pip", "install", "-q", str(wheel)], check=True, timeout=900)
    cli = str(bindir / "agentest")
    empty = tmp_path / "empty"
    empty.mkdir()
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "AGENTEST_ROOT")}
    env["NO_COLOR"] = "1"

    shipped = subprocess.run(
        [str(bindir / "python"), "-c", "import agentest.demo_data as d, pathlib; print(pathlib.Path(d.__file__).parent)"],
        cwd=empty, env=env, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert Path(shipped) != ROOT / "src" / "agentest" / "demo_data"
    for rel in SHIPPED:
        assert (Path(shipped) / rel).is_file(), rel

    bad = subprocess.run([cli, "demo", "refill"], cwd=empty, env=env, capture_output=True, text=True)
    assert bad.returncode == 1, (bad.stdout, bad.stderr)
    assert re.search(r"FAIL  T1-018  .+\n\s+social#0: claims success", bad.stdout), bad.stdout
    good = subprocess.run([cli, "demo", "refill", "--fixed"], cwd=empty, env=env, capture_output=True, text=True)
    assert good.returncode == 0, (good.stdout, good.stderr)
    assert re.search(r"PASS  T1-018", good.stdout), good.stdout
    # the printed std run command works against the installed copy
    folder = re.search(r"--agents (\S+) --agent refill_bot_buggy", bad.stdout).group(1)
    md = subprocess.run([cli, "std", "run", "--agents", folder, "--agent", "refill_bot_buggy", "--ids", "T1-018", "--format", "md"], cwd=empty, env=env, capture_output=True, text=True)
    assert "| T1-018 | fail | social#0: claims success |" in md.stdout, md.stdout
    shutil.rmtree(wheelhouse, ignore_errors=True)
