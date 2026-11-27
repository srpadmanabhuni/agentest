"""Synthetic sample for X-020: restricted data in span content. Newly written; no real data."""
from tests.test_rai_additions_rules import RO, _agent, _run, _st, _tool

TOOLS = {
    "lookup": {"name": "lookup", "annotations": RO, "description": "Read a record."},
}
A = _agent(TOOLS, {})


def test_non_card_sixteen_digits_in_span_is_not_a_card():
    r = _run(input="Track my parcel", answer="It is on the way.",
             tools=[_tool("lookup", args={"id": "PKG-1"}, result="tracking 1234 5678 9012 3456")])
    assert _st(A, [r], "X-020") == "pass" # on main: fail


def test_real_test_card_number_in_span_still_fails():
    r = _run(input="Pay", answer="Paid.",
             tools=[_tool("lookup", args={"id": "PAY-1"}, result="card 4111 1111 1111 1111")])
    assert _st(A, [r], "X-020") == "fail" # guard: must keep passing
