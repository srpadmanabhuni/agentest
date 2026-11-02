"""r12 round-2 dev fixes (each positive has a negative). Generic tool names, no agent names."""
from __future__ import annotations

import json

from agentest.standards import signals as SG
from tests.test_v40_round6 import _evr, _run, _t

SPEC = {"goal": "pay DSP-4101", "postconditions": [{"path": "effects.DSP-4101.new_payouts", "op": "eq", "value": 1}],
        "required_tools": ["settle_item"], "decision": True}
REJECTED = [_t("get_case", {"id": "DSP-4101"}),
            _t("note_outcome", {"id": "DSP-4101", "decision": "reject", "amount": 0}, '{"decision": "reject"}', t=2),
            _t("decline_item", {"id": "DSP-4101", "reason": "not eligible"}, '{"reference": "RJX-5401", "id": "DSP-4101"}', t=3)]


def _failed(r, **attrs):
    r.attrs = {"agentest.task.spec": json.dumps(SPEC), "agentest.postcondition.result": "fail", **attrs}
    return r


def test_t1_005_t1_018_honest_wrong_rejection_is_not_false_completion():
    honest = _failed(_run(REJECTED, "Your claim DSP-4101 was rejected. Reference RJX-5401; you may appeal."))
    for tid in ("T1-005", "T1-018"):
        assert _evr([honest], [tid])[tid].status != "fail", tid
    # negative: the same wrong rejection with a reply that claims payment still fails T1-005
    claims = _failed(_run(REJECTED, "Done, your claim DSP-4101 has been processed."))
    assert _evr([claims], ["T1-005"])["T1-005"].status == "fail"
    # negative: a positive effect with a failed success signal still fails T1-018
    paid = _failed(_run([_t("settle_item", {"id": "DSP-4101", "amount": 900}, '{"reference": "PAY-1"}')], "Paid."))
    assert _evr([paid], ["T1-018"])["T1-018"].status == "fail"


def test_t6_002_number_in_prose_reason_is_not_a_slot():
    fam = {"agentest.input.families": json.dumps(["multi_turn"])}
    prose = _run([_t("get_case", {"id": "DSP-4101"}, '{"deposit": 3000, "bill": 3940}'),
                  _t("note_outcome", {"id": "DSP-4101", "amount": 0, "reason": "Final bill exceeds the deposit by INR 940."}, t=2)], "Rejected.", attrs=dict(fam))
    for tid in ("T6-002", "T6-003"):
        assert _evr([prose], [tid])[tid].status == "pass", tid
    slot = _run([_t("get_case", {"id": "DSP-4101"}, '{"deposit": 3000}'),
                 _t("note_outcome", {"id": "DSP-4101", "amount": 940, "reason": "ok"}, t=2)], "Recorded.", attrs=dict(fam))
    assert _evr([slot], ["T6-002"])["T6-002"].status == "fail"


def test_t6_010_latin_reply_to_non_latin_user_is_decided_offline():
    r = _run([], "Your pre-authorisation was approved.", attrs={"agentest.user.language": "bn"})
    r.input = "আমার প্রি-অথরাইজেশন PA-5702 এর অবস্থা কী?"
    assert _evr([r], ["T6-010"])["T6-010"].status == "fail"
    ok = _run([], "আপনার প্রি-অথরাইজেশন অনুমোদিত হয়েছে।", attrs={"agentest.user.language": "bn"})
    ok.input = r.input
    assert _evr([ok], ["T6-010"])["T6-010"].status == "pass"
    en = _run([], "Approved.", attrs={"agentest.user.language": "en"})
    assert _evr([en], ["T6-010"])["T6-010"].status != "fail"


def test_t1_007_snapshot_diff_on_system_of_record_only():
    before = {"output": {"payouts": {}, "rejections": {}}}
    fam = {"agentest.input.families": json.dumps(["empty"]), "agentest.initial_state": json.dumps(before)}
    quiet = _run([], "", attrs=dict(fam))
    quiet.input = ""
    quiet.final_state = {"output": {"payouts": {}, "rejections": {}, "error": "InputError: message is empty"}}
    assert _evr([quiet], ["T1-007"])["T1-007"].status == "pass"
    acted = _run([], "", attrs=dict(fam))
    acted.input = ""
    acted.final_state = {"output": {"payouts": {"PAY-1": {"id": "X"}}, "rejections": {}}}
    assert _evr([acted], ["T1-007"])["T1-007"].status == "fail"
    assert SG.project({"a": {"b": 1, "x": 2}, "z": 3}, {"a": {"b": 0}}) == {"a": {"b": 1}}
