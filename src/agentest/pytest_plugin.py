"""pytest plugin: judge recorded agent traces with agentest from your own test suite.

Registered through the ``pytest11`` entry point, so it is available as soon as agentest is
installed next to pytest. pytest stays a test-time dependency: this module is only imported
by pytest. Nothing here runs unless a test asks for the ``agentest_check`` fixture.

Example::

    def test_my_agent(agentest_check):
        report = agentest_check("traces.otlp.jsonl", card="agent-card.json", tools="tools.json")
        report.assert_pass("T1-001", "T5-001")
        report.assert_no_fail()

Each call runs ``agentest std run --otlp ... --json ...`` in a subprocess with the current
interpreter, so verdicts are exactly the CLI's. Offline: no model, no network.
Command-line options: ``--agentest-mode`` (strict | examples; default examples, as in the CLI).
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path

STATUSES = ("pass", "fail", "n/a")


@dataclass
class AgentestReport:
    """Verdicts for one agent: ``cells`` maps test ID to ``{"status": ..., "detail": ...}``."""

    agent: str
    cells: dict[str, dict] = field(default_factory=dict)

    def status(self, test_id: str) -> str:
        cell = self.cells.get(test_id)
        if cell is None:
            raise KeyError(f"{test_id} is not in the agentest report for {self.agent}")
        return str(cell.get("status"))

    def ids(self, status: str) -> list[str]:
        return sorted(t for t, c in self.cells.items() if c.get("status") == status)

    def _explain(self, ids: Iterable[str]) -> str:
        return "\n".join(f"  {t}: {self.cells[t].get('status')} - {self.cells[t].get('detail', '')}" for t in ids)

    def assert_pass(self, *test_ids: str) -> None:
        """Every listed check must report ``pass`` (``n/a`` is not a pass)."""
        missing = [t for t in test_ids if t not in self.cells]
        assert not missing, f"not in the agentest report for {self.agent}: {missing}"
        bad = [t for t in test_ids if self.cells[t].get("status") != "pass"]
        assert not bad, f"agentest checks did not pass for {self.agent}:\n{self._explain(bad)}"

    def assert_no_fail(self, ignore: Iterable[str] = ()) -> None:
        """No check may report ``fail``, apart from the IDs in ``ignore``."""
        skip = set(ignore)
        bad = [t for t in self.ids("fail") if t not in skip]
        assert not bad, f"agentest reported fail for {self.agent}:\n{self._explain(bad)}"


def _as_str(p: str | PathLike[str]) -> str:
    return str(Path(p))


def run_agentest(
    otlp: str | PathLike[str] | Iterable[str | PathLike[str]],
    *,
    card: str | PathLike[str] | None = None,
    tools: str | PathLike[str] | None = None,
    ids: Iterable[str] | None = None,
    mode: str = "examples",
    workdir: str | PathLike[str],
) -> dict[str, AgentestReport]:
    """Run ``agentest std run --otlp`` and return one :class:`AgentestReport` per agent."""
    files = [otlp] if isinstance(otlp, (str, PathLike)) else list(otlp)
    for f in files + [p for p in (card, tools) if p is not None]:
        if not Path(f).is_file():
            raise FileNotFoundError(f"agentest input not found: {f}")
    out = Path(workdir) / "agentest-report.json"
    argv = [sys.executable, "-m", "agentest", "std", "run", "--otlp", *map(_as_str, files), "--mode", mode, "--json", str(out)]
    if card is not None:
        argv += ["--card", _as_str(card)]
    if tools is not None:
        argv += ["--tools", _as_str(tools)]
    if ids:
        argv += ["--ids", ",".join(ids)]
    proc = subprocess.run(argv, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"agentest exited {proc.returncode}: {proc.stderr or proc.stdout}")
    data = json.loads(out.read_text(encoding="utf-8"))
    return {agent: AgentestReport(agent, cells) for agent, cells in data.items()}


def pytest_addoption(parser) -> None:
    group = parser.getgroup("agentest")
    group.addoption(
        "--agentest-mode",
        choices=("strict", "examples"),
        default="examples",
        help="agentest evidence mode for the agentest_check fixture (default: examples, as in the CLI)",
    )


def _make_check(mode: str, tmp_path: Path):
    calls = 0

    def _check(otlp, *, card=None, tools=None, ids=None, agent: str | None = None) -> AgentestReport:
        nonlocal calls
        calls += 1
        work = tmp_path / f"agentest-{calls}"
        work.mkdir()
        reports = run_agentest(otlp, card=card, tools=tools, ids=ids, mode=mode, workdir=work)
        if agent is not None:
            if agent not in reports:
                raise KeyError(f"agent {agent!r} not in the report; found {sorted(reports)}")
            return reports[agent]
        if len(reports) != 1:
            raise ValueError(f"traces hold {len(reports)} agents {sorted(reports)}; pass agent=")
        return next(iter(reports.values()))

    return _check


def pytest_configure(config) -> None:
    """Register the ``agentest_check`` fixture. pytest is imported here, lazily, because it is
    not a runtime dependency of agentest; this hook only ever runs inside pytest."""
    try:
        import pytest
    except ImportError:  # pragma: no cover - the hook is only called by pytest
        return

    class _AgentestFixtures:
        @pytest.fixture
        def agentest_check(self, request, tmp_path):
            """Return ``agentest_check(otlp, card=None, tools=None, ids=None, agent=None)``.

            It judges trace files and returns the :class:`AgentestReport` for one agent. When the
            traces hold more than one agent, pass ``agent=``; use ``run_agentest`` for all of them.
            """
            return _make_check(request.config.getoption("--agentest-mode"), tmp_path)

    if not config.pluginmanager.has_plugin("agentest-fixtures"):
        config.pluginmanager.register(_AgentestFixtures(), "agentest-fixtures")
