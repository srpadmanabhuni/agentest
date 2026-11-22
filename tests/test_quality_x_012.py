"""Synthetic sample for X-012: invented currency amount. Newly written; no real data."""
from tests.test_rai_additions_rules import RO, _agent, _run, _st, _tool

TOOLS = {
    "lookup": {"name": "lookup", "annotations": RO, "description": "Read a record."},
}
A = _agent(TOOLS, {})


def _answer(text):
    return [_run(input="Refund 150 INR", answer=text, tools=[_tool("lookup", args={}, result="{}")])]


def test_amount_followed_by_a_currency_word_is_checked():
    assert _st(A, _answer("Refunded 5000 rupees."), "X-012") == "fail"   # on main: n/a


def test_amount_followed_by_a_currency_code_is_checked():
    assert _st(A, _answer("Refunded 5000 INR."), "X-012") == "fail"      # on main: n/a


def test_grounded_amount_passes():
    assert _st(A, _answer("Refunded 150 INR."), "X-012") == "pass"


def test_grounded_amount_with_a_currency_word_passes():
    assert _st(A, _answer("Refunded 150 rupees."), "X-012") == "pass"


def test_number_without_a_currency_is_not_an_amount():
    assert _st(A, _answer("Ticket 5000 is closed."), "X-012") == "n/a"
