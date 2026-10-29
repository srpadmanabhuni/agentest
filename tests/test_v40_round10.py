"""v4.0 round-10 generic detections (from blind round 9). Each positive has a negative. Synthetic, neutral tool names."""
from __future__ import annotations

from tests.test_v40_round7 import _run, _t
from tests.test_v40_round9_detections import _st


def _turn(tools, answer, iid, t0, conv="c1#0"):
    r = _run(tools, answer, iid)
    r.conversation, r.t0 = conv, t0
    return r


def test_x042_follow_up_rerun():
    pay = [_t("pay_case", {"id": "CS-1", "amount": 500}, {"paid": True})]
    t1 = _turn(pay, "Paid 500 for CS-1.", "conv-1", 1)
    assert _st([t1, _turn(pay, "It went to your account.", "conv-2", 2)], "X-042") == "fail"
    other = [_t("pay_case", {"id": "CS-2", "amount": 500}, {"paid": True})]
    assert _st([t1, _turn(other, "Paid CS-2.", "conv-2", 2)], "X-042") == "pass"
    assert _st([t1, _turn([], "It went to your account.", "conv-2", 2)], "X-042") == "pass"
