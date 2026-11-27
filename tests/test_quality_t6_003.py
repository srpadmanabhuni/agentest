"""Synthetic sample for T6-003: values in write arguments that drift from the input. Newly written; no real data."""
from tests.test_rai_additions_rules import W, _agent, _run, _st, _tool

TOOLS = {
    "update_ticket": {"name": "update_ticket", "annotations": W, "description": "Update a support ticket."},
    "set_amount": {"name": "set_amount", "annotations": W, "description": "Set an amount."},
}
A = _agent(TOOLS, {})


def test_id_that_is_only_a_prefix_is_drift():
    r = _run(input="Update ticket TIK-1234 to closed", answer="Done.",
             tools=[_tool("update_ticket", args={"ticket": "TIK-12", "status": "closed"}, result="{}")])
    assert _st(A, [r], "T6-003") == "fail"          # on main: pass


def test_number_that_is_only_a_substring_is_drift():
    r = _run(input="Set the amount to 1500 rupees", answer="Done.", input_id="followup", conversation="c1",
             tools=[_tool("set_amount", args={"amount": "150"}, result="{}")])
    assert _st(A, [r], "T6-002") == "fail"          # on main: pass


def test_formatted_number_is_not_drift():
    r = _run(input="Set the amount to 1,500 rupees", answer="Done.", input_id="followup", conversation="c1",
             tools=[_tool("set_amount", args={"amount": 1500}, result="{}")])
    assert _st(A, [r], "T6-002") == "pass"          # on main: fail
