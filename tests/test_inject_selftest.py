"""v4.0 r10: generic defect injection. From clean synthetic traces, each injected defect is caught by a named check."""
from agentest.standards.inject import MUTATIONS, garble_reply, self_test, shift_date
from tests.test_v34_round3_fixes import no_judge
from tests.test_v40_round7 import _run, _t
from tests.test_v40_round9_detections import _agent

RD = _t("get_case", {"id": "CS-1"}, {"id": "CS-1", "payable_inr": 900, "locked_units": 45, "due_date": "2026-11-05"})
PAY = _t("pay_case", {"id": "CS-1", "amount": 900, "decision": "approve"}, {"paid": True, "decision": "approve"}, t=2)
CLEAN = [_run([RD, PAY], "Paid 900 for CS-1 on approval. 45 units are locked and were not paid. "
                         "Your next instalment of CS-1 falls due on 2026-11-05."),
         _run([RD, PAY], "CS-1 के लिए 900 रुपये का भुगतान कर दिया गया है। 45 इकाइयाँ लॉक हैं।", "hi_0")]
EXPECT = {"flip-decision": "X-038", "repeat-write": "T2-003", "drop-disclosure": "X-048", "shift-date": "X-047",
          "garble-reply": "X-046"}


def test_every_injected_defect_is_caught():
    with no_judge():
        res = self_test(_agent(), CLEAN)
    assert set(res) == set(MUTATIONS) == set(EXPECT)
    for m, want in EXPECT.items():
        assert res[m] and want in res[m]["caught_by"], (m, res[m])


def test_mutators_skip_what_they_cannot_mutate():
    r = _run([RD], "Done.")
    assert shift_date(_agent(), r) is None and garble_reply(_agent(), r) is None
    assert all(fn(_agent(), _run([], "ok")) is None for fn in MUTATIONS.values())
