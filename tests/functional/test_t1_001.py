"""T1-001 — Pass golden / Fail broken_agent.

What this module verifies: oracles in this pack accept correct (golden) behaviour and reject
seeded defects (broken), plus CLI exit-code contracts used in CI. Algorithms, thresholds and
per-ID references are in profiles/_lib/samples.yaml (expect_notes); background: Hoare 1969 postconditions; Kahn 1962 topological order; tau-bench pass^k (arXiv:2406.12045).
Full bibliography: docs/REFERENCES.md.
"""

from __future__ import annotations

from agentest.agents import broken as broken_agent
from agentest.agents import golden as golden_agent
from agentest.cases.registry import episode, judge
from agentest.cli import main as cli_main
from agentest.env import APPROVED, PENDING, REJECTED
from agentest.fixtures.ledger import fresh_env_t1_001
from agentest.runner import run_ids
from agentest.samples.record import snap
from agentest.types import Outcome


def test_fresh_ledger_is_pending():
    """Fixture sanity: a fresh ledger seeds every record as PENDING, so T1-001 postconditions cannot hold before the agent acts."""
    env = fresh_env_t1_001()
    assert env.ledger.snapshot() == {
        "R1": PENDING,
        "R2": PENDING,
        "R3": PENDING,
        "R4": PENDING,
        "R5": PENDING,
    }


def test_t1_001_pass_golden():
    """T1-001 (terminal postconditions, Hoare-style): golden run reaches expected ledger state and the oracle returns PASS."""
    env = fresh_env_t1_001()
    trace = golden_agent.run(env)
    result = judge("T1-001", [episode("t", "T1-001", 0, env, trace, snap)])
    assert result.outcome is Outcome.PASS
    assert "false_completion=0" in result.reason
    assert env.ledger.get("R1") == APPROVED
    assert env.ledger.get("R2") == APPROVED
    assert env.ledger.get("R3") == APPROVED
    assert env.ledger.get("R4") == REJECTED
    assert env.ledger.get("R5") == PENDING  # unchanged_except


def test_t1_001_fail_broken_false_completion():
    """T1-001: broken agent claims success without writing - oracle must report FAIL (false completion)."""
    env = fresh_env_t1_001()
    trace = broken_agent.run(env)
    result = judge("T1-001", [episode("t", "T1-001", 0, env, trace, snap)])
    assert result.outcome is Outcome.FAIL
    assert result.reason.startswith("false completion")
    assert trace.claims_success is True
    # No correct writes
    assert env.ledger.get("R1") == PENDING
    assert env.ledger.get("R4") == PENDING


def test_runner_golden_passes():
    """Runner API path for T1-001 returns PASS for golden."""
    results = run_ids(["T1-001"], agent="golden")
    assert len(results) == 1
    assert results[0].ok


def test_runner_broken_fails():
    """Runner API path for T1-001 returns FAIL for broken."""
    results = run_ids(["T1-001"], agent="broken")
    assert len(results) == 1
    assert not results[0].ok
    assert results[0].outcome is Outcome.FAIL


def test_cli_golden_exit_0():
    """CLI T1-001 golden exits 0."""
    assert cli_main(["run", "--suite", "functional", "--ids", "T1-001", "--agent", "golden"]) == 0


def test_cli_broken_exit_nonzero():
    """CLI T1-001 broken exits non-zero."""
    code = cli_main(["run", "--suite", "functional", "--ids", "T1-001", "--agent", "broken"])
    assert code != 0
