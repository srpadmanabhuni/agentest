"""Orchestration pack — Pass golden / Fail broken for catalogue theme IDs.

What this module verifies: oracles in this pack accept correct (golden) behaviour and reject
seeded defects (broken), plus CLI exit-code contracts used in CI. Algorithms, thresholds and
per-ID references are in profiles/_lib/samples.yaml (expect_notes); background: Saltzer & Schroeder 1975 (least privilege); Hardy 1988 (confused deputy); RFC 6749 single-use codes; EU AI Act Art. 14.
Full bibliography: docs/REFERENCES.md.
"""

from __future__ import annotations

import pytest

from agentest.cases.registry import ORCHESTRATION_IDS
from agentest.cli import main as cli_main
from agentest.runner import run_ids
from agentest.types import Outcome

# New CaseSpecs (T3-006 is reused from explainability — still in suite list)
NEW_ORCH_IDS = [i for i in ORCHESTRATION_IDS if i != "T3-006"]


@pytest.mark.parametrize("checklist_id", ORCHESTRATION_IDS)
def test_golden_passes(checklist_id: str):
    """Each orchestration ID must PASS for the golden reference trajectory. Guards against oracle false negatives (an oracle rejecting correct behaviour). See expect_notes in profiles/_lib/samples.yaml for algorithm and references."""
    results = run_ids([checklist_id], suite="orchestration", agent="golden")
    assert len(results) == 1
    assert results[0].outcome is Outcome.PASS, results[0]


@pytest.mark.parametrize("checklist_id", ORCHESTRATION_IDS)
def test_broken_fails(checklist_id: str):
    """Each orchestration ID must FAIL for the broken trajectory (seeded defect). Guards against oracle false positives / vacuous oracles - the mutation-testing idea that a test must kill a known-bad variant."""
    results = run_ids([checklist_id], suite="orchestration", agent="broken")
    assert len(results) == 1
    assert results[0].outcome is Outcome.FAIL, results[0]


def test_suite_golden_all_pass():
    """Running the whole orchestration suite with the golden agent yields only PASS outcomes (suite-level wiring check)."""
    results = run_ids(None, suite="orchestration", agent="golden")
    assert len(results) == 8
    assert all(r.ok for r in results), [(r.checklist_id, r.reason) for r in results if not r.ok]


def test_suite_alias_orch():
    """The `orch` alias resolves to the orchestration pack."""
    results = run_ids(None, suite="orch", agent="golden")
    assert len(results) == 8
    assert all(r.ok for r in results)


def test_cli_orchestration_golden_exit_0():
    """CLI orchestration suite with golden exits 0."""
    assert cli_main(["run", "--suite", "orchestration", "--agent", "golden"]) == 0


def test_cli_orchestration_broken_exit_nonzero():
    """CLI orchestration suite with broken exits non-zero."""
    assert cli_main(["run", "--suite", "orchestration", "--agent", "broken"]) != 0


@pytest.mark.parametrize("agent", ["scripted", "policy", "reflective", "supervisor", "handoff", "planner", "critic", "federation"])
def test_passing_samples_pass_orchestration_suite(agent: str):
    """Every green-ladder sample agent (scripted..federation) passes the orchestration suite."""
    results = run_ids(None, suite="orchestration", agent=agent)
    assert len(results) == 8
    assert all(r.ok for r in results), [(r.checklist_id, r.reason) for r in results if not r.ok]


def test_noop_fails_handover_prose():
    """The noop agent must FAIL T3-001 (handover prose is not an approval token)."""
    results = run_ids(["T3-001"], suite="orchestration", agent="noop")
    assert results[0].outcome is Outcome.FAIL


def test_eager_fails_hitl():
    """The eager agent must FAIL the HITL-before-disburse check (T2-004)."""
    results = run_ids(["T2-004"], suite="orchestration", agent="eager")
    assert results[0].outcome is Outcome.FAIL


def test_prior_suites_still_green():
    """Regression guard: adding this pack did not break earlier suites for golden."""
    assert cli_main(["run", "--suite", "functional", "--agent", "golden"]) == 0
    assert cli_main(["run", "--suite", "privacy", "--agent", "golden"]) == 0
    assert cli_main(["run", "--suite", "explainability", "--agent", "golden"]) == 0
    assert cli_main(["run", "--suite", "bias_fairness", "--agent", "golden"]) == 0


def test_new_ids_implemented():
    """Every ID in ORCHESTRATION_IDS has a CaseSpec in the registry."""
    assert set(NEW_ORCH_IDS) == {
        "T3-001",
        "T3-002",
        "T3-007",
        "T3-010",
        "T3-011",
        "T3-014",
        "T2-004",
    }
