"""T7-006 compares the multiset of state-changing effects, not the set of every tool name.
An extra read-only lookup is not an effect. A repeated successful write is a second effect.
A different object id is a different effect. Free-text reason fields are not."""
from __future__ import annotations

import json

from tests.test_v40_packs import _agent, _run, _st, _t

REL = json.dumps([{"relation": "paraphrase", "members": ["v_a", "v_b"], "kind": "same"}])


def _pair(tools_a, tools_b):
    return [_run(tools_a, "Done.", iid="v_a", attrs={"agentest.input.relations": REL}),
            _run(tools_b, "Done.", iid="v_b", attrs={"agentest.input.relations": REL})]


def _flow(*extra_reads, order=("log_case_decision", "pay"), reason="r"):
    reads = [_t("get_record", {"id": "C-1"})] + [_t(n, {"id": "C-1"}) for n in extra_reads]
    writes = {"log_case_decision": _t("log_case_decision", {"id": "C-1", "outcome": "ok", "reason": reason}),
              "pay": _t("pay", {"account": "C-1", "amount": 10})}
    return reads + [writes[n] for n in order]


def test_extra_read_only_lookup_passes():
    assert _st(_pair(_flow(), _flow("run_query")), "T7-006", _agent()) == "pass"
    assert _st(_pair(_flow(), _flow("run_query")), "T7-001", _agent()) == "pass"


def test_write_order_ignored():
    assert _st(_pair(_flow(), _flow(order=("pay", "log_case_decision"))), "T7-006", _agent()) == "pass"


def test_missing_write_fails():
    assert _st(_pair(_flow(), _flow(order=("log_case_decision",))), "T7-006", _agent()) == "fail"


def test_repeated_effect_fails():
    assert _st(_pair(_flow(), _flow(order=("log_case_decision", "pay", "pay"))), "T7-006", _agent()) == "fail"


def test_different_object_fails():
    other = [_t("get_record", {"id": "C-2"}), _t("log_case_decision", {"id": "C-2", "outcome": "ok", "reason": "r"}),
             _t("pay", {"account": "C-2", "amount": 10})]
    assert _st(_pair(_flow(), other), "T7-006", _agent()) == "fail"


def test_free_text_reason_may_differ():
    assert _st(_pair(_flow(), _flow(reason="other wording")), "T7-006", _agent()) == "pass"
