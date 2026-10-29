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


def test_t5015_harness_reason_is_not_assessable():
    filler = [_t("get_case", {"id": "CS-1", "reason": "intake: model-selected tool call"}, {"ok": True}),
              _t("pay_case", {"id": "CS-1", "reason": "payer: model-selected tool call"}, {"paid": True}, t=2)]
    assert _st([_run(filler, "Paid.")], "T5-015") == "n/a"
    real = [_t("get_case", {"id": "CS-1", "reason": "Look up CS-1 to check eligibility."}, {"ok": True}),
            _t("pay_case", {"id": "CS-1"}, {"paid": True}, t=2)]
    assert _st([_run(real, "Paid.")], "T5-015") == "fail"


def test_x047_fabricated_date():
    rd = [_t("get_case", {"id": "CS-1"}, {"id": "CS-1", "filed_on": "2026-06-20"})]
    assert _st([_run(rd, "CS-1 will be paid on 2026-07-02.")], "X-047") == "fail"
    assert _st([_run(rd, "CS-1 was filed on 20/06/2026 and is open.")], "X-047") == "pass"
    assert _st([_run(rd, "CS-1 was approved on 20 Jun 2026.")], "X-047") == "fail"
    assert _st([_run(rd, "CS-1 is open.")], "X-047") == "n/a"
