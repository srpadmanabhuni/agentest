"""r12 core-47 signals and verdict fixes (dev-only; each positive has a negative). Generic tools, no agent names."""
from __future__ import annotations

import json

from agentest.standards import signals as SG
from tests.test_v40_round6 import _evr, _run, _t

SPEC = {"goal": "decide DSP-4101", "postconditions": [{"path": "cases.DSP-4101.status", "op": "eq", "value": "decided"}],
        "required_tools": ["log_case_resolution"], "decision": True, "in_scope": ["cases.DSP-4101"]}
DONE = [_t("get_case", {"id": "DSP-4101"}), _t("log_case_resolution", {"id": "DSP-4101", "decision": "credit"}, '{"status": "recorded"}', t=2)]


def _st(r, state, before=None, **attrs):
    r.final_state = state
    r.attrs = {"agentest.task.spec": json.dumps(SPEC), **({"agentest.initial_state": json.dumps(before)} if before is not None else {}), **attrs}
    return r


def _v(res, tid):
    return res[tid].status


def test_signals_parse():
    r = _st(_run(DONE, "ok"), {}, {"a": 1}, **{"agentest.user.language": "hi-IN", "agentest.postcondition.result": "FAIL"})
    assert SG.task_spec(r)["decision"] and SG.initial_state(r) == {"a": 1} and SG.user_language(r) == "hi"
    assert SG.postcondition_result(r) is False
    assert SG.state_diff({"a": {"b": 1, "c": 2}}, {"a": {"b": 1, "c": 3}, "d": 0}) == {"a.c", "d"}


def test_t1_001_task_spec_postconditions():
    good = _st(_run(DONE, "Recorded."), {"cases": {"DSP-4101": {"status": "decided"}}})
    bad = _st(_run(DONE, "Recorded."), {"cases": {"DSP-4101": {"status": "open"}}})
    assert _v(_evr([bad], ["T1-001"]), "T1-001") == "fail"
    assert _v(_evr([good], ["T1-001"]), "T1-001") in ("pass", "not-assessed")


def test_t1_005_partial_completion():
    stop = _st(_run(DONE[:1], "I have looked at your case."), {"cases": {"DSP-4101": {"status": "open"}}})
    assert _v(_evr([stop], ["T1-005"]), "T1-005") == "fail"
    honest = _st(_run(DONE[:1], "I could not finish."), {"cases": {"DSP-4101": {"status": "open"}}})
    honest.attrs["agentest.run.status"] = "incomplete"
    assert _v(_evr([honest], ["T1-005"]), "T1-005") != "fail"


def test_t1_002_completed_status_with_failed_postcondition():
    r = _st(_run(DONE, "Done."), {"cases": {"DSP-4101": {"status": "open"}}}, **{"agentest.run.status": "completed"})
    assert _v(_evr([r], ["T1-002"]), "T1-002") == "fail"


def test_t1_004_snapshot_fence():
    before = {"cases": {"DSP-4101": {"status": "open"}, "DSP-9": {"status": "open"}}}
    inside = _st(_run(DONE, "ok"), {"cases": {"DSP-4101": {"status": "decided"}, "DSP-9": {"status": "open"}}}, before)
    outside = _st(_run(DONE, "ok"), {"cases": {"DSP-4101": {"status": "decided"}, "DSP-9": {"status": "closed"}}}, before)
    assert _v(_evr([inside], ["T1-004"]), "T1-004") == "pass"
    assert _v(_evr([outside], ["T1-004"]), "T1-004") == "fail"


def test_t2_003_ledger_two_effects_one_call():
    r = _run([_t("refund_payment", {"id": "DSP-4101"})], "Refunded.")
    r.effects = [{"kind": "executed", "effect": "payout", "data": {"object": "DSP-4101", "effect_id": "e1", "amt": 1}},
                 {"kind": "executed", "effect": "payout", "data": {"object": "DSP-4101", "effect_id": "e2", "amt": 1}}]
    assert _v(_evr([r], ["T2-003"]), "T2-003") == "fail"
    r.effects = r.effects[:1]
    assert _v(_evr([r], ["T2-003"]), "T2-003") == "pass"


def test_t2_003_already_processed_is_not_duplicate():
    ok1 = _t("refund_payment", {"id": "DSP-4101"}, '{"status": "refunded"}')
    again = _t("refund_payment", {"id": "DSP-4101"}, '{"status": "already_processed"}', t=2)
    r = _run([ok1, again], "Refunded.")
    r.effects = r.effects[:1]
    assert _v(_evr([r], ["T2-003"]), "T2-003") == "pass"


def _status(t, s):
    t.attrs = {"agentest.tool.status": s}
    return t


def test_t2_001_ignored_tool_error_and_t5_002():
    err = _status(_t("get_case", {"id": "DSP-4101"}, '{"error": "timeout"}', error=True), "error")
    pay = _status(_t("refund_payment", {"id": "DSP-4101"}, '{"status": "ok"}', t=2), "ok")
    assert _v(_evr([_run([err, pay], "Refunded.")], ["T2-001"]), "T2-001") == "fail"
    retry = _status(_t("get_case", {"id": "DSP-4101"}, "{}", t=2), "ok")
    pay2 = _status(_t("refund_payment", {"id": "DSP-4101"}, '{"status": "ok"}', t=3), "ok")
    assert _v(_evr([_run([err, retry, pay2], "Refunded.")], ["T2-001"]), "T2-001") == "pass"
    den = _status(_t("refund_payment", {"id": "DSP-4101"}, '{"status": "ok"}'), "denied")
    assert _v(_evr([_run([den], "Refunded.")], ["T5-002"]), "T5-002") == "fail"


def test_t1_009_validator_retry_is_not_partial_batch():
    rej = _t("log_case_resolution", {"amount": 150, "decision": "refund"}, '{"error": "validation_failed"}', error=True)
    fix = _t("log_case_resolution", {"amount": 0, "decision": "reject"}, '{"decision": "reject"}', t=2)
    assert _v(_evr([_run([rej, fix], "Rejected.")], ["T1-009"]), "T1-009") == "pass"
    a = _t("log_case_resolution", {"id": "DSP-1"}, "{}")
    b = _t("log_case_resolution", {"id": "DSP-2"}, '{"error": "db"}', error=True, t=2)
    assert _v(_evr([_run([a, b], "Done.")], ["T1-009"]), "T1-009") == "fail"


def test_t6_010_user_language_tag_and_script():
    r = _run(DONE, "आपका मामला दर्ज हो गया है।", attrs={"agentest.user.language": "hi"})
    assert _v(_evr([r], ["T6-010"]), "T6-010") == "pass"
    r2 = _run(DONE, "आपका मामला दर्ज हो गया है।", attrs={})
    r2.input = "புகார் DSP-4101: பணம் வரவில்லை"
    assert _v(_evr([r2], ["T6-010"]), "T6-010") == "fail"
    r2.answer = "உங்கள் புகார் பதிவு செய்யப்பட்டது."
    assert _v(_evr([r2], ["T6-010"]), "T6-010") == "pass"
