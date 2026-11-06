#!/usr/bin/env python3
"""LangGraph flagship demo: import recorded message-list episodes, run checks, print a sample report.

Synthetic / offline only. No LangGraph package, no model, no network.
agentest's only runtime dependency remains PyYAML (distribution name agentest-ai).

  python examples/langgraph_import/test_langgraph.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / "examples" / "langgraph_import"
NATIVE = EX / "native" / "expense_bot.jsonl"
MAP = EX / "import" / "map.json"
AGENTS = EX / "agents"
CARD = EX / "agents" / "expense_bot" / "agent-card.json"
TOOLS = EX / "agents" / "expense_bot" / "tools.json"
GOLDEN_OTLP = EX / "agents" / "expense_bot" / "traces" / "expense_bot.otlp.jsonl"
# Small illustrative slice only — not a published scoreboard.
SAMPLE_IDS = ("T1-001", "T2-001", "T5-001")


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not prev else src + os.pathsep + prev
    env.pop("AGENTEST_HUB_CATALOGUE", None)
    return env


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "agentest", *argv],
        cwd=ROOT,
        env=_cli_env(),
        text=True,
        capture_output=True,
    )


def _fail(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def main() -> int:
    for path in (NATIVE, MAP, CARD, TOOLS, AGENTS):
        if not path.exists():
            _fail(f"missing example path: {path.relative_to(ROOT)}")

    with tempfile.TemporaryDirectory() as td:
        out_otlp = Path(td) / "expense_bot.otlp.jsonl"
        report = Path(td) / "report.json"
        imp = _run(
            [
                "std",
                "import",
                str(NATIVE),
                "--map",
                str(MAP),
                "--tools",
                str(TOOLS),
                "--service",
                "expense_bot",
                "--out",
                str(out_otlp),
            ]
        )
        if imp.returncode != 0:
            _fail(imp.stderr or imp.stdout or f"import exited {imp.returncode}")
        if not out_otlp.is_file():
            _fail("import did not write OTLP output")
        if GOLDEN_OTLP.is_file() and out_otlp.read_text(encoding="utf-8") != GOLDEN_OTLP.read_text(
            encoding="utf-8"
        ):
            _fail("imported OTLP drifted from examples/langgraph_import/agents/expense_bot/traces/")

        # Prefer --agents so the report key matches the folder name.
        run = _run(
            [
                "std",
                "run",
                "--agents",
                str(AGENTS),
                "--json",
                str(report),
            ]
        )
        if run.returncode != 0:
            _fail(run.stderr or run.stdout or f"run exited {run.returncode}")
        if not report.is_file():
            _fail("run did not write the JSON report")
        data = json.loads(report.read_text(encoding="utf-8"))

    agent_block = data.get("expense_bot")
    if not isinstance(agent_block, dict):
        _fail(f"expected expense_bot in report, got {sorted(data)[:8]}")

    print("LangGraph flagship example — expense_bot (synthetic message lists)")
    print("Path: import (langgraph_msgs) → std run → sample report")
    print("Docs: docs/integrations/langgraph.md")
    print()
    print("Sample checks (illustrative only; open the JSON report for the full set):")
    print("| ID | status | detail (truncated) |")
    print("|---|---|---|")
    for tid in SAMPLE_IDS:
        cell = agent_block.get(tid)
        if not isinstance(cell, dict):
            print(f"| {tid} | missing | |")
            continue
        detail = " ".join(str(cell.get("detail") or "").split())[:120]
        print(f"| {tid} | {cell.get('status')} | {detail} |")
    print()
    print("Bring an agent trace, contribute a test — see CONTRIBUTING.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
