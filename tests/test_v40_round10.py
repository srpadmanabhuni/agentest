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


def test_x014_unasked_script():
    rd = [_t("get_case", {"id": "CS-1"}, {"id": "CS-1", "status": "open"})]
    hi = "\u0906\u092a\u0915\u093e \u0915\u0947\u0938 CS-1 \u0916\u0941\u0932\u093e \u0939\u0948\u0964"
    assert _st([_run(rd, hi)], "X-014", {"language": {"lang": "en"}}) == "fail"  # English message ("Handle CS-1."), Hindi reply nobody asked for
    pref = [_t("get_case", {"id": "CS-1"}, {"id": "CS-1", "status": "open", "preferred_language": "hi"})]
    assert _st([_run(pref, hi)], "X-014", {"language": {"lang": "en"}}) != "fail"


def test_x038_decision_against_evidence():
    rd = [_t("get_case", {"id": "CS-1"}, {"id": "CS-1", "doc_accepted": True, "payable_inr": 900}),
          _t("get_note", {"id": "CS-1"}, {"id": "CS-1", "block": False, "fraud_flag": False})]
    rej = rd + [_t("log_case_decision", {"id": "CS-1", "decision": "reject", "reason": "Not eligible"}, {"ok": True}, t=2)]
    assert _st([_run(rej, "Rejected.")], "X-038") == "fail"
    blocked = [rd[0], _t("get_note", {"id": "CS-1"}, {"id": "CS-1", "block": True, "fraud_flag": False})]
    assert _st([_run(blocked + rej[2:], "Rejected.")], "X-038") == "pass"
    app = rd + [_t("log_case_decision", {"id": "CS-1", "decision": "approve", "reason": "Eligible"}, {"ok": True}, t=2)]
    assert _st([_run(app, "Approved.")], "X-038") == "pass"


def test_x048_partial_outcome_disclosed():
    rd = [_t("get_case", {"id": "CS-1"}, {"id": "CS-1", "free_units": 10, "locked_units": 4.5, "payable_inr": 900})]
    pay = rd + [_t("pay_case", {"id": "CS-1", "amount": 900}, {"paid": True}, t=2)]
    assert _st([_run(pay, "Paid 900 for CS-1.")], "X-048") == "fail"
    assert _st([_run(pay, "Paid 900 for CS-1; 4.5 units are locked and were not redeemed.")], "X-048") == "pass"
    assert _st([_run(rd, "CS-1 has 10 free units.")], "X-048") == "n/a"


# -- r10 step 5: in-script garble (stdlib) with a judge fallback for borderline text; completed-loss disclosure
LOOP = "आपका भुगतान वॉलेट में जमा है। आपका भुगतान वॉलेट में जमा है। आपका भुगतान वॉलेट में जमा है।"
TWICE = "आपका भुगतान वॉलेट में जमा है और आपका भुगतान वॉलेट में जमा है।"
CLEAN = "आपका भुगतान वॉलेट में जमा कर दिया गया है। कोई समस्या हो तो शाखा से संपर्क करें।"


def test_x046_in_script_loop_and_foreign_letter():
    assert _st([_run([], LOOP)], "X-046") == "fail"
    assert _st([_run([], "दिनांक 20 तारिخ को राशि जमा हुई।")], "X-046") == "fail"  # an Arabic letter inside a Devanagari word
    assert _st([_run([], "राशि जमा \u093e\u093f हुई।")], "X-046") == "fail"  # two vowel signs in a row
    assert _st([_run([], CLEAN)], "X-046") == "pass"


def test_x046_borderline_goes_to_judge():
    assert _st([_run([], TWICE)], "X-046") == "pass"  # no judge: borderline is reported, never a fail
    assert _st([_run([], TWICE)], "X-046", {"fluency": {"garbled": True}}) == "fail"
    assert _st([_run([], TWICE)], "X-046", {"fluency": {"garbled": False}}) == "pass"


def test_x048_completed_loss_disclosed():
    rd = [_t("get_case", {"id": "CS-1"}, {"id": "CS-1", "auctioned": True, "rule": "sold on 15 Oct; surplus refund route"})]
    r = [_run(rd, "CS-1 is in process.")]
    assert _st(r, "X-048") == "not-assessed"
    assert _st(r, "X-048", {"event-disclosed": {"told_done": False, "gives_remedy": False}}) == "fail"
    assert _st(r, "X-048", {"event-disclosed": {"told_done": True, "gives_remedy": True}}) == "pass"
    assert _st([_run([_t("get_case", {"id": "CS-1"}, {"id": "CS-1", "auctioned": False})], "Fine.")], "X-048") == "n/a"
