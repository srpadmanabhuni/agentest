"""Explainability pack — Pass golden / Fail broken for all 5 catalogue IDs.

What this module verifies: oracles in this pack accept correct (golden) behaviour and reject
seeded defects (broken), plus CLI exit-code contracts used in CI. Algorithms, thresholds and
per-ID references are in profiles/_lib/samples.yaml (expect_notes); background: Faithfulness (Jacovi & Goldberg 2020, doi:10.18653/v1/2020.acl-main.386); ReAct (Yao et al. 2023, arXiv:2210.03629); trajectory evaluation (arXiv:2510.02837).
Full bibliography: docs/REFERENCES.md.
"""

from __future__ import annotations

import pytest

from agentest.cases.registry import EXPLAINABILITY_IDS
from agentest.cli import main as cli_main
from agentest.runner import run_ids
from agentest.types import Outcome

IMPLEMENTED = list(EXPLAINABILITY_IDS)


@pytest.mark.parametrize("checklist_id", IMPLEMENTED)
def test_golden_passes(checklist_id: str):
    """Each explainability ID must PASS for the golden reference trajectory. Guards against oracle false negatives (an oracle rejecting correct behaviour). See expect_notes in profiles/_lib/samples.yaml for algorithm and references."""
    results = run_ids([checklist_id], suite="explainability", agent="golden")
    assert len(results) == 1
    assert results[0].outcome is Outcome.PASS, results[0]


@pytest.mark.parametrize("checklist_id", IMPLEMENTED)
def test_broken_fails(checklist_id: str):
    """Each explainability ID must FAIL for the broken trajectory (seeded defect). Guards against oracle false positives / vacuous oracles - the mutation-testing idea that a test must kill a known-bad variant."""
    results = run_ids([checklist_id], suite="explainability", agent="broken")
    assert len(results) == 1
    assert results[0].outcome is Outcome.FAIL, results[0]


def test_suite_golden_all_pass():
    """Running the whole explainability suite with the golden agent yields only PASS outcomes (suite-level wiring check)."""
    results = run_ids(None, suite="explainability", agent="golden")
    assert len(results) == 5
    assert all(r.ok for r in results), [(r.checklist_id, r.reason) for r in results if not r.ok]


def test_cli_explainability_golden_exit_0():
    """CLI explainability suite with golden exits 0."""
    assert cli_main(["run", "--suite", "explainability", "--agent", "golden"]) == 0


def test_cli_explainability_broken_exit_nonzero():
    """CLI explainability suite with broken exits non-zero."""
    assert cli_main(["run", "--suite", "explainability", "--agent", "broken"]) != 0


def test_prior_suites_still_green():
    """Regression guard: adding this pack did not break earlier suites for golden."""
    assert cli_main(["run", "--suite", "functional", "--agent", "golden"]) == 0
    assert cli_main(["run", "--suite", "privacy", "--agent", "golden"]) == 0
