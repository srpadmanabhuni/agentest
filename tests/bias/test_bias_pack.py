"""Bias/fairness pack — Pass golden / Fail broken for all 3 catalogue IDs.

What this module verifies: oracles in this pack accept correct (golden) behaviour and reject
seeded defects (broken), plus CLI exit-code contracts used in CI. Algorithms, thresholds and
per-ID references are in profiles/_lib/samples.yaml (expect_notes); background: Metamorphic testing (Chen et al. 1998, arXiv:2002.12543); counterfactual token fairness (Garg et al. 2019, doi:10.1145/3306618.3317950).
Full bibliography: docs/REFERENCES.md.
"""

from __future__ import annotations

import pytest

from agentest.cases.registry import BIAS_FAIRNESS_IDS
from agentest.cli import main as cli_main
from agentest.runner import run_ids
from agentest.types import Outcome

IMPLEMENTED = list(BIAS_FAIRNESS_IDS)


@pytest.mark.parametrize("checklist_id", IMPLEMENTED)
def test_golden_passes(checklist_id: str):
    """Each bias / fairness ID must PASS for the golden reference trajectory. Guards against oracle false negatives (an oracle rejecting correct behaviour). See expect_notes in profiles/_lib/samples.yaml for algorithm and references."""
    results = run_ids([checklist_id], suite="bias_fairness", agent="golden")
    assert len(results) == 1
    assert results[0].outcome is Outcome.PASS, results[0]


@pytest.mark.parametrize("checklist_id", IMPLEMENTED)
def test_broken_fails(checklist_id: str):
    """Each bias / fairness ID must FAIL for the broken trajectory (seeded defect). Guards against oracle false positives / vacuous oracles - the mutation-testing idea that a test must kill a known-bad variant."""
    results = run_ids([checklist_id], suite="bias_fairness", agent="broken")
    assert len(results) == 1
    assert results[0].outcome is Outcome.FAIL, results[0]


def test_suite_golden_all_pass():
    """Running the whole bias / fairness suite with the golden agent yields only PASS outcomes (suite-level wiring check)."""
    results = run_ids(None, suite="bias_fairness", agent="golden")
    assert len(results) == 3
    assert all(r.ok for r in results)


def test_bias_alias_matches_bias_fairness():
    """The `bias` suite alias resolves to exactly BIAS_FAIRNESS_IDS."""
    a = run_ids(None, suite="bias", agent="golden")
    b = run_ids(None, suite="bias_fairness", agent="golden")
    assert [r.checklist_id for r in a] == [r.checklist_id for r in b]
    assert all(r.ok for r in a)


def test_cli_bias_fairness_golden_exit_0():
    """CLI bias_fairness suite with golden exits 0."""
    assert cli_main(["run", "--suite", "bias_fairness", "--agent", "golden"]) == 0


def test_cli_bias_alias_golden_exit_0():
    """CLI accepts the `bias` alias and exits 0 for golden."""
    assert cli_main(["run", "--suite", "bias", "--agent", "golden"]) == 0


def test_cli_bias_broken_exit_nonzero():
    """CLI bias suite with broken exits non-zero."""
    assert cli_main(["run", "--suite", "bias", "--agent", "broken"]) != 0


def test_prior_suites_still_green():
    """Regression guard: adding this pack did not break earlier suites for golden."""
    assert cli_main(["run", "--suite", "functional", "--agent", "golden"]) == 0
    assert cli_main(["run", "--suite", "privacy", "--agent", "golden"]) == 0
    assert cli_main(["run", "--suite", "explainability", "--agent", "golden"]) == 0
