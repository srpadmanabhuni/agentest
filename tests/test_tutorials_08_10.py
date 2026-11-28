"""Tutorials 8 to 10 run as written: the files they ask you to save are extracted from the Markdown and executed."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TUT = ROOT / "docs" / "tutorials"
SAVE = re.compile(r"Save this as `([\w.]+)`[^\n]*\n\n```python\n(.*?)```", re.S)


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _save(doc: str, folder: Path) -> list[str]:
    names = []
    for name, body in SAVE.findall((TUT / doc).read_text(encoding="utf-8")):
        (folder / name).write_text(body, encoding="utf-8")
        names.append(name)
    return names


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=_env(), text=True, capture_output=True, timeout=300)


def _agentest(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return _run([sys.executable, "-m", "agentest", *args], cwd)


def _pytest(target: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", target], cwd)


def test_tutorial_08_red_on_the_skipped_lookup_then_green(tmp_path):
    assert _save("08-pytest-regression-from-a-failed-run.md", tmp_path) == ["make_files.py", "runs.py", "test_refund_runs.py"]
    assert _run([sys.executable, "make_files.py"], tmp_path).returncode == 0
    red = _pytest("test_refund_runs.py", tmp_path)
    assert red.returncode == 1, red.stdout
    assert "T2-001: fail" in red.stdout and "T2-013: fail" in red.stdout
    test = tmp_path / "test_refund_runs.py"
    test.write_text(test.read_text(encoding="utf-8").replace("SKIPPED_LOOKUP as RUN", "LOOKUP_FIRST as RUN"), encoding="utf-8")
    green = _pytest("test_refund_runs.py", tmp_path)
    assert green.returncode == 0, green.stdout


def test_tutorial_09_only_new_failures_fail_the_gate(tmp_path):
    _save("08-pytest-regression-from-a-failed-run.md", tmp_path)
    assert _save("09-offline-otel-traces-new-failures-only.md", tmp_path) == ["save_runs.py"]
    assert _run([sys.executable, "make_files.py"], tmp_path).returncode == 0
    saved = _run([sys.executable, "save_runs.py"], tmp_path)
    assert saved.returncode == 0, saved.stderr
    card = ["--card", "agent/agent-card.json", "--tools", "agent/tools.json"]
    for name in ("before", "after"):
        run = _agentest(["std", "run", "--otlp", f"{name}.otlp.jsonl", *card, "--json", f"{name}.json"], tmp_path)
        assert run.returncode == 0, run.stderr
    before = _agentest(["std", "run", "--otlp", "before.otlp.jsonl", *card], tmp_path)
    assert "(T2-004, T2-012)" in before.stdout
    worse = _agentest(["std", "diff", "before.json", "after.json", "--fail-on-new-fail"], tmp_path)
    assert worse.returncode == 1
    assert "newly failing: 3" in worse.stdout and "T2-001  pass -> fail" in worse.stdout
    assert "T2-004" not in worse.stdout and "T2-012" not in worse.stdout
    better = _agentest(["std", "diff", "after.json", "before.json", "--fail-on-new-fail"], tmp_path)
    assert better.returncode == 0 and "newly failing: 0" in better.stdout
    emit = _agentest(["std", "run", "--otlp", "after.otlp.jsonl", *card, "--emit-otlp", "verdicts.otlp.json"], tmp_path)
    assert emit.returncode == 0 and "gen_ai.evaluation.result" in (tmp_path / "verdicts.otlp.json").read_text(encoding="utf-8")


def test_tutorial_10_one_test_for_three_frameworks(tmp_path):
    _save("08-pytest-regression-from-a-failed-run.md", tmp_path)
    assert _save("10-one-test-three-frameworks.md", tmp_path) == ["recordings.py", "adapters.py", "test_three_frameworks.py"]
    assert _run([sys.executable, "make_files.py"], tmp_path).returncode == 0
    result = _pytest("test_three_frameworks.py", tmp_path)
    assert result.returncode == 0, result.stdout
    assert "6 passed" in result.stdout
