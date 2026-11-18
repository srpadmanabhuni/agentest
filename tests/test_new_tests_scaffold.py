"""Scaffold for the opt-in Phase 1 New tests (NT-xxx): registry, catalogue fragments and default-set isolation.

Holds for any number of batches: every catalogue row has a rule and every NT rule has a row; NT IDs never enter the
default 130; `--ids NT` selects the New tests and, when batch 3 is present, T1-020 and T1-021.
"""
from __future__ import annotations

import json
import re

from agentest.cli import main
from agentest.standards import rules
from agentest.standards.catalog import ALL_IDS, NEW_TEST_IDS, new_tests

NT_RX = re.compile(r"^NT-\d{3}$")
REQUIRED = {"id", "class_id", "title", "article_test", "article_title", "objective", "acceptance_criteria", "trace_attributes", "batch"}


def test_rows_and_rules_agree():
    nt_rules = {k for k in rules.RULES if k.startswith("NT-")}
    assert nt_rules == set(NEW_TEST_IDS)
    assert list(NEW_TEST_IDS) == sorted(NEW_TEST_IDS)
    for i, r in new_tests().items():
        assert NT_RX.match(i) and r["class_id"] == "NT"
        assert REQUIRED <= set(r), (i, REQUIRED - set(r))
        assert re.match(r"^A\d{3}$", r["article_test"])


def test_new_tests_stay_out_of_the_default_set():
    assert not set(NEW_TEST_IDS) & set(ALL_IDS)
    assert len(ALL_IDS) == 130
    res = rules.evaluate(*_eager(), mode="examples")
    assert not any(k.startswith("NT-") for k in res)


def _phase1_shipped():
    try:
        from agentest.standards.new_tests.b3 import PHASE1_SHIPPED
        return tuple(PHASE1_SHIPPED)
    except ImportError:
        return ()


def test_list_new_tests(capsys):
    assert main(["list", "--new-tests"]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    shipped = _phase1_shipped()
    if shipped:
        assert out[-1] == (
            f"{len(NEW_TEST_IDS)} New test(s) and {len(shipped)} shipped Phase 1 design(s) "
            "(opt-in; not in the default 110/130)"
        )
        listed = {line.split()[0] for line in out[:-1]}
        assert set(NEW_TEST_IDS) <= listed and set(shipped) <= listed
    else:
        assert out[-1] == f"{len(NEW_TEST_IDS)} New test(s) (opt-in; not in the default 110/130)"


def test_std_run_ids_nt_shorthand(capsys):
    shipped = _phase1_shipped()
    if not NEW_TEST_IDS and not shipped:
        return
    assert main(["std", "run", "--agent", "eager", "--ids", "NT", "--format", "json"]) == 0
    rows = json.loads(capsys.readouterr().out)["results"]
    assert sorted(r["id"] for r in rows) == sorted(set(NEW_TEST_IDS) | set(shipped))
    assert {r["status"] for r in rows} <= {"pass", "fail", "n/a"}


def _eager():
    from agentest.standards.metadata import load_all
    from agentest.standards.runner import runs

    a = load_all()["eager"]
    return a, runs(a)
