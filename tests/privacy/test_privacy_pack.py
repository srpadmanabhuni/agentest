"""Privacy pack — Pass golden / Fail broken for all 8 catalogue IDs.

What this module verifies: oracles in this pack accept correct (golden) behaviour and reject
seeded defects (broken), plus CLI exit-code contracts used in CI. Algorithms, thresholds and
per-ID references are in profiles/_lib/samples.yaml (expect_notes); background: NIST SP 800-122; GDPR; indirect prompt injection (Greshake et al. 2023, doi:10.1145/3605764.3623985); metamorphic testing for T7-014.
Full bibliography: docs/REFERENCES.md.
"""

from __future__ import annotations

import pytest

from agentest.cases.registry import PRIVACY_IDS
from agentest.cli import main as cli_main
from agentest.runner import run_ids
from agentest.types import Outcome

IMPLEMENTED = list(PRIVACY_IDS)


@pytest.mark.parametrize("checklist_id", IMPLEMENTED)
def test_golden_passes(checklist_id: str):
    """Each privacy ID must PASS for the golden reference trajectory. Guards against oracle false negatives (an oracle rejecting correct behaviour). See expect_notes in profiles/_lib/samples.yaml for algorithm and references."""
    results = run_ids([checklist_id], suite="privacy", agent="golden")
    assert len(results) == 1
    assert results[0].outcome is Outcome.PASS, results[0]


@pytest.mark.parametrize("checklist_id", IMPLEMENTED)
def test_broken_fails(checklist_id: str):
    """Each privacy ID must FAIL for the broken trajectory (seeded defect). Guards against oracle false positives / vacuous oracles - the mutation-testing idea that a test must kill a known-bad variant."""
    results = run_ids([checklist_id], suite="privacy", agent="broken")
    assert len(results) == 1
    assert results[0].outcome is Outcome.FAIL, results[0]


def test_suite_golden_all_pass():
    """Running the whole privacy suite with the golden agent yields only PASS outcomes (suite-level wiring check)."""
    results = run_ids(None, suite="privacy", agent="golden")
    assert len(results) == 8
    assert all(r.ok for r in results), [(r.checklist_id, r.reason) for r in results if not r.ok]


def test_cli_privacy_golden_exit_0():
    """CLI `agentest run --suite privacy --agent golden` exits 0 (all pass)."""
    assert cli_main(["run", "--suite", "privacy", "--agent", "golden"]) == 0


def test_cli_privacy_broken_exit_nonzero():
    """CLI with the broken agent exits non-zero so CI pipelines fail on regressions."""
    assert cli_main(["run", "--suite", "privacy", "--agent", "broken"]) != 0


def test_functional_still_green():
    """Regression guard: functional suite still all-pass for golden after adding privacy."""
    assert cli_main(["run", "--suite", "functional", "--agent", "golden"]) == 0
