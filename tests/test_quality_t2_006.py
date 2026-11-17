"""Synthetic parent/child traces for T2-006; no real data."""
import json

import pytest

from tests.test_rai_additions_rules import W, _agent, _run, _st, _tool

TOOLS = {
    "create_order": {"name": "create_order", "annotations": W, "description": "Create an order."},
    "add_item": {"name": "add_item", "annotations": W, "description": "Add an item to an order."},
}
A = _agent(TOOLS, {})


@pytest.mark.parametrize("argument_key", ["order_id", "orderId", "order-id", "ORDER_ID"])
@pytest.mark.parametrize("result_key", ["order_id", "orderId", "order-id", "ORDER_ID", "orderID"])
@pytest.mark.parametrize("parent_first", [False, True])
def test_parent_order_across_id_spellings(argument_key, result_key, parent_first):
    child = _tool("add_item", args={argument_key: "ORD-90", "sku": "W1"}, result="{}", t=2 if parent_first else 1)
    parent = _tool("create_order", args={}, result=json.dumps({result_key: "ORD-90"}), t=1 if parent_first else 2)
    run = _run(input="Add a widget to the new order", answer="Added.",
               tools=[parent, child] if parent_first else [child, parent])
    assert _st(A, [run], "T2-006") == ("pass" if parent_first else "fail")


@pytest.mark.parametrize("key", ["order_id", "orderId", "order-id", "ORDER_ID"])
def test_id_supplied_in_input_does_not_require_a_prior_parent(key):
    run = _run(input="Add a widget to ORD-90", answer="Added.", tools=[
        _tool("add_item", args={key: "ORD-90"}, result="{}", t=1),
        _tool("create_order", args={}, result=json.dumps({key: "ORD-90"}), t=2),
    ])
    assert _st(A, [run], "T2-006") == "n/a"


@pytest.mark.parametrize("key", ["paid", "valid", "guid", "uuid", "PAID", "id"])
@pytest.mark.parametrize("parent_first", [False, True])
def test_non_id_words_do_not_create_parent_dependencies(key, parent_first):
    child = _tool("add_item", args={key: True}, result="{}", t=2 if parent_first else 1)
    parent = _tool("create_order", args={}, result=json.dumps({key: True}), t=1 if parent_first else 2)
    run = _run(input="Add a widget to the new order", answer="Added.",
               tools=[parent, child] if parent_first else [child, parent])
    assert _st(A, [run], "T2-006") == "n/a"


@pytest.mark.parametrize("argument_key,result_key", [("pa_id", "paid"), ("paid", "pa_id")])
def test_non_id_words_cannot_alias_an_id_kind(argument_key, result_key):
    run = _run(input="Add a widget to the new order", answer="Added.", tools=[
        _tool("add_item", args={argument_key: "ORD-90"}, result="{}", t=1),
        _tool("create_order", args={}, result=json.dumps({result_key: "ORD-90"}), t=2),
    ])
    assert _st(A, [run], "T2-006") == "n/a"


@pytest.mark.parametrize("parent_first", [False, True])
def test_nested_producer_preserves_camel_case_boundary(parent_first):
    child = _tool("add_item", args={"order_id": "ORD-90"}, result="{}", t=2 if parent_first else 1)
    parent = _tool("create_order", args={}, result=json.dumps({"orders": [{"orderId": "ORD-90"}]}),
                   t=1 if parent_first else 2)
    run = _run(input="Add a widget to the new order", answer="Added.",
               tools=[parent, child] if parent_first else [child, parent])
    assert _st(A, [run], "T2-006") == ("pass" if parent_first else "fail")
