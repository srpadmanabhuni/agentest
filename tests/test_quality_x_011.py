"""Synthetic sample for X-011: invented identifiers in answers. Newly written; no real data."""
from tests.test_rai_additions_rules import RO, _agent, _run, _st, _tool

TOOLS = {
    "lookup": {"name": "lookup", "annotations": RO, "description": "Read a record."},
}
A = _agent(TOOLS, {})


def _answer(text):
    return [_run(input="Where is my order?", answer=text,
                 tools=[_tool("lookup", args={"order": "ORD-12"}, result='{"order": "ORD-12", "status": "shipped"}')])]


def test_lowercase_id_is_checked():
    assert _st(A, _answer("Order ord-48213 has shipped."), "X-011") == "fail"   # on main: n/a


def test_hash_number_id_is_checked():
    assert _st(A, _answer("Order #48213 has shipped."), "X-011") == "fail"      # on main: n/a


def test_grounded_id_passes():
    assert _st(A, _answer("Order ORD-12 has shipped."), "X-011") == "pass"      # guard


def test_everyday_hyphenated_tokens_are_not_flagged():
    text = "Order ORD-12 shipped per iso-8601 schedule; no covid-19 delay on gpt-40."
    assert _st(A, _answer(text), "X-011") == "pass"
