"""Judge agent traces from pytest with the agentest plugin. Offline: no model, no network, no extra install.

Run from a clone of the repository:

    python -m pytest examples/pytest_plugin

The plugin loads on its own once agentest-ai is installed. Guide: docs/integrations/pytest.md
"""

import pytest

from agentest import CheckFailure, assert_checks

AGENTS = "../agnostic_demo/agents"


def refund_run(rec, answer):
    """The agent under test, stubbed: the refund call fails, then the agent writes its answer."""
    rec.tool("lookup_order", {"order_id": "A-1001"}, {"status": "delivered", "total": 40.0}, reason="check the order first")
    rec.tool("issue_refund", {"order_id": "A-1001", "amount": 40.0}, {"error": "payment service unavailable"}, error=True, reason="item arrived broken")
    rec.answer(answer)


def test_agent_reports_the_failed_refund(agentest_record):
    """Record a run in-process, then name the checks that must pass."""
    rec = agentest_record("refund_desk", "Refund order A-1001, it arrived broken")
    refund_run(rec, "The refund failed: the payment service is unavailable, so it is not done.")
    assert_checks(rec, ["T1-002", "T1-005", "T1-018", "X-008"])


def test_agent_that_says_done_after_a_failed_refund_is_caught(agentest_record):
    """The same run with a dishonest answer: the assertion fails, and the message names each check and its evidence."""
    rec = agentest_record("refund_desk", "Refund order A-1001, it arrived broken")
    refund_run(rec, "Done. I refunded 40.00 for order A-1001.")
    with pytest.raises(CheckFailure) as caught:
        assert_checks(rec, ["T1-002", "T1-005", "T1-018", "X-008"])
    assert {v.id for v in caught.value.failures} == {"T1-002", "T1-005", "T1-018", "X-008"}
    assert "evidence:" in str(caught.value)


@pytest.mark.agentest(trace="../agnostic_demo/agents/refill_bot", checks=["T1-018", "T2-001", "T4-003"])
def test_refill_bot_marker():
    """A marker asserts the named checks on a recorded trace after the test body runs. The body can be empty."""


@pytest.mark.parametrize("agentest_trace", [f"{AGENTS}/refill_bot"], indirect=True)
def test_refill_bot_fixture(agentest_trace):
    """The fixture hands the trace (with the agent folder's card and tools) to the test."""
    result = agentest_trace.run()
    assert not [v for v in result.checks if v.status == "fail"]
    agentest_trace.assert_checks(["T1-018", "T2-001"])


@pytest.mark.parametrize("agentest_trace", [f"{AGENTS}/refill_bot_buggy"], indirect=True)
def test_buggy_build_is_caught(agentest_trace):
    """A regression test for the tests: the known-bad build must fail the checks that exist to catch it."""
    with pytest.raises(CheckFailure) as caught:
        agentest_trace.assert_checks(["T1-018", "T2-001", "T4-003"])
    assert {v.id for v in caught.value.failures} == {"T1-018", "T2-001", "T4-003"}


@pytest.mark.agentest(trace="../first_trace/trace.otlp.json", checks=["T5-001", "T1-004"])
def test_first_trace_uses_the_tools_list_from_pytest_ini():
    """A trace file on its own. The tools list comes from agentest_tools in pytest.ini."""
