"""Public Python calls stay on the CLI's checks: same verdicts, same summary, same exit code."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import agentest
from agentest.cli import main
from agentest.standards.cli import UnknownTestIds, restrict_ids
from agentest.standards.verdict_diff import diff_verdicts

ROOT = Path(__file__).resolve().parents[1]
START = 1_700_000_000_000_000_000


def _example_cases() -> list[tuple[str, str]]:
    """Trace inputs under examples/: one agent directory, a directory of them, or a loose OTLP file."""
    examples = ROOT / "examples"
    rows: list[tuple[str, str]] = []
    roots: list[str] = []
    for card in sorted(examples.rglob("agent-card.json")):
        agent = card.parent
        if not (any(agent.glob("traces/*")) or any(agent.glob("*.otlp.json*"))):
            continue
        rows.append(("agent", agent.relative_to(ROOT).as_posix()))
        parent = agent.parent.relative_to(ROOT).as_posix()
        if parent not in roots:
            roots.append(parent)
            rows.append(("agents", parent))
    for path in sorted(examples.rglob("*")):
        if not path.is_file():
            continue
        if path.parent.name == "traces":
            continue
        if path.name.endswith((".otlp.json", ".otlp.jsonl")) or path.suffix == ".pb":
            rows.append(("file", path.relative_to(ROOT).as_posix()))
    rows.append(("generated", "examples/otel_plain/emit_trace.py"))
    return rows


CASES = _example_cases()


def _sidecars(trace: Path) -> tuple[Path | None, Path | None]:
    card = trace.parent / "agent-card.json"
    tools = trace.parent / "tools.json"
    return (card if card.is_file() else None, tools if tools.is_file() else None)


def _prepare(kind: str, rel: str, tmp_path: Path) -> tuple[Path, Path | None, Path | None]:
    if kind == "generated":
        proc = subprocess.run([sys.executable, str(ROOT / rel)], cwd=ROOT, capture_output=True, text=True, check=True)
        dest = tmp_path / "emit_trace.otlp.json"
        dest.write_text(proc.stdout, encoding="utf-8")
        plain = ROOT / "examples" / "otel_plain"
        return dest, plain / "agent-card.json", plain / "tools.json"
    path = ROOT / rel
    if kind == "file":
        card, tools = _sidecars(path)
        return path, card, tools
    return path, None, None


def _cli(args: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, dict]:
    code = main(args)
    out = capsys.readouterr().out
    json_path = Path(args[args.index("--json") + 1])
    return code, out, json.loads(json_path.read_text(encoding="utf-8"))


def _statuses(data: dict) -> dict[str, dict[str, str]]:
    return {agent: {test_id: cell["status"] for test_id, cell in row.items()} for agent, row in data.items()}


@pytest.mark.parametrize("mode", ["examples", "strict"])
@pytest.mark.parametrize("kind,rel", CASES)
def test_cli_and_api_verdicts_match(kind: str, rel: str, mode: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path, card, tools = _prepare(kind, rel, tmp_path)
    out = tmp_path / "cli.json"
    args = ["std", "run", "--json", str(out), "--mode", mode, "--strict"]
    if kind == "agent":
        args += ["--agents", str(path.parent), "--agent", path.name]
    elif kind == "agents":
        args += ["--agents", str(path)]
    else:
        args += ["--otlp", str(path)]
        if card:
            args += ["--card", str(card)]
        if tools:
            args += ["--tools", str(tools)]
    code, text, cli = _cli(args, capsys)
    result = agentest.run(path, card=card, tools=tools, mode=mode, strict=True)
    report = diff_verdicts(_statuses(cli), _statuses(result.verdicts))
    assert report["transitions"] == [], report
    assert cli == result.verdicts
    assert code == result.exit_code
    assert text == str(result) + "\n"
    assert agentest.Result(result.verdicts, mode, strict=False).exit_code == 0


def test_module_cli_matches_api_on_recorded_example(tmp_path: Path) -> None:
    """``python -m agentest`` (the CLI) and ``agentest.run`` on one example trace."""
    trace = ROOT / "examples" / "start_here" / "claims-success.otlp.json"
    out = tmp_path / "cli.json"
    env = dict(os.environ)
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run(
        [sys.executable, "-m", "agentest", "std", "run", "--otlp", str(trace), "--json", str(out), "--strict", "--ids", "T1-018,T1-005"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )
    assert proc.returncode in (0, 1), proc.stderr
    result = agentest.run(trace, strict=True, ids="T1-018,T1-005")
    cli = json.loads(out.read_text(encoding="utf-8"))
    report = diff_verdicts(_statuses(cli), _statuses(result.verdicts))
    assert report["transitions"] == [], report
    assert cli == result.verdicts
    assert proc.returncode == result.exit_code
    assert proc.stdout == str(result) + "\n"


def test_loose_run_exit_code_matches_cli_without_strict(capsys: pytest.CaptureFixture[str]) -> None:
    buggy = ROOT / "examples" / "agnostic_demo" / "agents" / "refill_bot_buggy"
    code = main(["std", "run", "--agents", str(buggy.parent), "--agent", buggy.name])
    capsys.readouterr()
    assert code == 0
    assert agentest.run(buggy, strict=False).exit_code == 0


def test_ids_selection_matches_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    agent = ROOT / "examples" / "agnostic_demo" / "agents" / "refill_bot"
    out = tmp_path / "cli.json"
    code, text, cli = _cli(
        ["std", "run", "--agents", str(agent.parent), "--agent", agent.name, "--ids", "T1-018,T5-001", "--json", str(out)],
        capsys,
    )
    result = agentest.run(agent, ids=["T1-018", "T5-001"])
    assert diff_verdicts(_statuses(cli), _statuses(result.verdicts))["transitions"] == []
    assert cli == result.verdicts
    assert set(result.verdicts[agent.name]) == {"T1-018", "T5-001"}
    assert code == result.exit_code == 0
    assert text == str(result) + "\n"


def test_missing_trace_and_bad_mode_raise() -> None:
    with pytest.raises(agentest.RunError) as missing:
        agentest.run("no-such-trace.otlp.json")
    assert missing.value.exit_code == 2
    assert "not a file" in str(missing.value)
    with pytest.raises(agentest.RunError):
        agentest.run("no-such-trace.otlp.json", mode="loud")


def test_unknown_ids_use_the_cli_message(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(UnknownTestIds) as err:
        restrict_ids({}, {}, "T9-999", "examples")
    assert str(err.value).startswith("unknown test IDs: T9-999")
    monkeypatch.setattr("agentest.standards.runner.run_all", lambda ags, mode="examples", ids=None: {key: {} for key in ags})
    monkeypatch.setattr("agentest.standards.runner.to_json", lambda res: res)
    trace = ROOT / "examples" / "start_here" / "claims-success.otlp.json"
    with pytest.raises(agentest.RunError, match="unknown test IDs: T9-999") as raised:
        agentest.run(trace, ids="T9-999")
    assert raised.value.exit_code == 2


def test_assert_passes_follows_strict_and_named_checks() -> None:
    failing = agentest.Result(
        {"shop": {"T1-001": {"status": "n/a", "detail": "no signal"}, "T1-002": {"status": "fail", "detail": "nope"}}},
        strict=False,
    )
    with pytest.raises(AssertionError, match="T1-002"):
        agentest.assert_passes(failing)
    with pytest.raises(AssertionError, match="T1-001"):
        agentest.assert_passes(failing, "T1-001")
    passing = agentest.Result({"shop": {"T1-001": {"status": "pass", "detail": "ok"}}}, strict=True)
    agentest.assert_passes(passing)
    agentest.assert_passes(passing, "T1-001")
    assert passing["T1-001"].status == "pass"
    assert passing.exit_code == 0


def _fill(rec: agentest.Recorder) -> None:
    rec.tool("lookup", {"q": "mug"}, {"ok": True})
    rec.step("Looked up the mug.")
    rec.answer("Found a mug.")


def test_record_matches_cli_and_decorator(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with agentest.record("shop", input_text="Find a mug", start_ns=START) as rec:
        _fill(rec)
        dest = rec.write(tmp_path / "shop.otlp.jsonl")
        recorded = rec.check(strict=True)
    out = tmp_path / "cli.json"
    code, text, cli = _cli(["std", "run", "--otlp", str(dest), "--json", str(out), "--strict"], capsys)
    report = diff_verdicts(_statuses(cli), _statuses(recorded.verdicts))
    assert report["transitions"] == [], report
    assert cli == recorded.verdicts
    assert code == recorded.exit_code
    assert text == str(recorded) + "\n"
    from agentest.standards.otel import from_otlp

    episode = from_otlp(rec.otlp())
    assert any(tool.name == "lookup" for tool in episode.tools)
    assert "Found a mug." in episode.answer

    @agentest.record("shop", input_text="Find a mug", start_ns=START)
    def shop(handle: agentest.Recorder) -> str:
        _fill(handle)
        return "Found a mug."

    assert shop() == "Found a mug."
    assert shop.result is not None
    assert shop.result.verdicts == recorded.verdicts

    @agentest.record("shop", start_ns=START)
    def boom(handle: agentest.Recorder) -> None:
        handle.tool("lookup", {}, {})
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError, match="nope"):
        boom()
    assert boom.result is None


def test_public_surface_exports_and_does_not_import_pytest() -> None:
    assert {"run", "assert_passes", "record", "Recorder", "Result", "Verdict", "RunError", "__version__"} <= set(agentest.__all__)
    tree = ast.parse((ROOT / "src" / "agentest" / "api.py").read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    assert "pytest" not in modules
