"""Functional pack — Pass golden / Fail broken for all 18 catalogue IDs.

What this module verifies: oracles in this pack accept correct (golden) behaviour and reject
seeded defects (broken), plus CLI exit-code contracts used in CI. Algorithms, thresholds and
per-ID references are in profiles/_lib/samples.yaml (expect_notes); background: Hoare 1969 postconditions; Kahn 1962 topological order; tau-bench pass^k (arXiv:2406.12045).
Full bibliography: docs/REFERENCES.md.
"""

from __future__ import annotations

import pytest

from agentest.cases.registry import FUNCTIONAL_IDS
from agentest.cli import main as cli_main
from agentest.runner import run_ids
from agentest.types import Outcome

IMPLEMENTED = list(FUNCTIONAL_IDS)


@pytest.mark.parametrize("checklist_id", IMPLEMENTED)
def test_golden_passes(checklist_id: str):
    """Each functional ID must PASS for the golden reference trajectory. Guards against oracle false negatives (an oracle rejecting correct behaviour). See the oracle docstrings in src/agentest/cases/t1 / t2 / t5 / t6 / multi_run.py for algorithm and references."""
    results = run_ids([checklist_id], suite="functional", agent="golden")
    assert len(results) == 1
    assert results[0].outcome is Outcome.PASS, results[0]


@pytest.mark.parametrize("checklist_id", IMPLEMENTED)
def test_broken_fails(checklist_id: str):
    """Each functional ID must FAIL for the broken trajectory (seeded defect). Guards against oracle false positives / vacuous oracles - the mutation-testing idea that a test must kill a known-bad variant."""
    results = run_ids([checklist_id], suite="functional", agent="broken")
    assert len(results) == 1
    assert results[0].outcome is Outcome.FAIL, results[0]


def test_suite_golden_all_pass():
    """Running the whole functional suite with the golden agent yields only PASS outcomes (suite-level wiring check)."""
    results = run_ids(None, suite="functional", agent="golden")
    assert len(results) == 18
    assert all(r.ok for r in results), [(r.checklist_id, r.outcome, r.reason) for r in results if not r.ok]


def test_cli_suite_golden_exit_0():
    """CLI functional suite with golden exits 0."""
    assert cli_main(["run", "--suite", "functional", "--agent", "golden"]) == 0


def test_cli_suite_broken_exit_nonzero():
    """CLI functional suite with broken exits non-zero."""
    assert cli_main(["run", "--suite", "functional", "--agent", "broken"]) != 0


def test_cli_single_broken_exit_nonzero():
    """CLI single-ID run with broken exits non-zero."""
    for checklist_id in IMPLEMENTED:
        code = cli_main(
            ["run", "--suite", "functional", "--ids", checklist_id, "--agent", "broken"]
        )
        assert code != 0, checklist_id
