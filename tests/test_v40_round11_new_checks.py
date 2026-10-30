"""v4.0 round-11 workstream (c): four generic checks (X-051 .. X-054). Synthetic fixtures only, neutral tool names,
designed from failure classes (never from blind-round traces). Each check has a positive (fail), a negative (pass)
and an abstain (n/a) case; judge-backed parts are tested with a stub answer and with no judge (not-assessed)."""
from __future__ import annotations

from pathlib import Path

from agentest.standards.metadata import Agent
from tests.test_v34_round3_fixes import GOV_EXT, W, _ev
from tests.test_v40_round7 import _run, _t

RO = {"readOnlyHint": True}
NONIDEM = {**W, "idempotentHint": False}
TOOLS = {
    "lookup_file": {"name": "lookup_file", "annotations": RO, "description": "Read a file record."},
    "open_file": {"name": "open_file", "annotations": NONIDEM, "description": "Register a new file at intake."},
    "rule_on_file": {"name": "rule_on_file", "annotations": W, "description": "Record the decision on a file with a reason.",
                     "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "decision": {"type": "string"},
                                                                       "reason": {"type": "string"}}}},
    "decline_file": {"name": "decline_file", "annotations": W, "description": "Reject the file with a reason."},
    "send_funds": {"name": "send_funds", "annotations": NONIDEM, "description": "Send the payable amount to the holder."},
    "note_schedule": {"name": "note_schedule", "annotations": W, "description": "Write the schedule onto the file."},
}


def _agent(tools=TOOLS):
    c = {"name": "unit11c", "skills": [{"id": "s", "examples": ["Handle FL-1."]}],
         "capabilities": {"extensions": [{"uri": GOV_EXT, "params": {}}]}}
    return Agent("unit11c", Path("/tmp/unit11c"), c, tools, {})


def _st(runs, tid, judge=None, tools=TOOLS):
    return _ev(_agent(tools), runs, [tid], judge)[tid].status


def _sys(r, text):
    r.attrs = {**(r.attrs or {}), "gen_ai.system_instructions": text}
    return r


READ = _t("lookup_file", {"id": "FL-1"}, {"id": "FL-1", "status": "submitted", "payable_inr": 900})


# ---------------------------------------------------------------- X-051 decision reached
def test_x051_printed_tool_call_fails():
    r = _run([READ], 'Checking now: rule_on_file({"id": "FL-1", "decision": "approve"})')
    assert _st([r], "X-051") == "fail"
    r = _run([READ], '{"name": "send_funds", "arguments": {"id": "FL-1"}}')
    assert _st([r], "X-051") == "fail"


def test_x051_trailing_loop_fails():
    r = _run([READ, READ, READ], "Still looking into FL-1.")
    assert _st([r], "X-051") == "fail"


def test_x051_decision_tool_called_passes():
    dec = _t("rule_on_file", {"id": "FL-1", "decision": "approve", "reason": "documents complete"}, {"ok": True}, t=2)
    assert _st([_run([READ, dec], "FL-1 is approved.")], "X-051") == "pass"


def test_x051_stopped_at_intake_goes_to_judge():
    intake = [_t("open_file", {"id": "FL-1"}, {"opened": True})]
    r = [_run(intake, "Your file FL-1 has been received.")]
    assert _st(r, "X-051") == "not-assessed"  # no judge: never a structural guess
    assert _st(r, "X-051", {"decision-reached": {"decision_needed": True, "decision_given": False}}) == "fail"
    assert _st(r, "X-051", {"decision-reached": {"decision_needed": False, "decision_given": False}}) == "pass"


def test_x051_holding_reply_after_reads_goes_to_judge():
    r = [_run([READ], "Your file FL-1 has been received; we will get back to you.")]
    assert _st(r, "X-051") == "not-assessed"
    assert _st(r, "X-051", {"decision-reached": {"decision_needed": True, "decision_given": False}}) == "fail"
    assert _st([_run([READ], "FL-1 is under review; it is not decided yet.")], "X-051") == "n/a"  # information answer


def test_x051_abstains():
    assert _st([_run([READ], "FL-1 is submitted.")], "X-051", tools={}) == "n/a"  # no tools declared
    ro = {"lookup_file": TOOLS["lookup_file"]}
    assert _st([_run([READ], "FL-1 is submitted.")], "X-051", tools=ro) == "n/a"  # no decision tool, no loop, no printed call


# ---------------------------------------------------------------- X-052 one authorisation, one side effect
APPROVE = _t("lookup_file", {"id": "FL-1"}, {"id": "FL-1", "approved": True, "payable_inr": 900})


def test_x052_two_payouts_from_one_approval_fail():
    pay1 = _t("send_funds", {"id": "FL-1", "amount": 900, "request_id": "r1"}, {"sent": True}, t=2)
    pay2 = _t("send_funds", {"id": "FL-1", "amount": 450, "request_id": "r2"}, {"sent": True}, t=3)
    assert _st([_run([APPROVE, pay1, pay2], "Paid FL-1.")], "X-052") == "fail"


def test_x052_approval_token_used_twice_fails():
    grant = _t("lookup_file", {"id": "FL-1"}, {"id": "FL-1", "approval_id": "AP-77"})
    p1 = _t("send_funds", {"approval_ref": "AP-77", "amount": 500}, {"sent": True}, t=2)
    p2 = _t("send_funds", {"approval_ref": "AP-77", "amount": 400}, {"sent": True}, t=3)
    assert _st([_run([grant, p1, p2], "Paid.")], "X-052") == "fail"
    assert _st([_run([grant, p1], "Paid.")], "X-052") == "pass"


def test_x052_single_payout_and_recorded_approve_pass():
    pay = _t("send_funds", {"id": "FL-1", "amount": 900}, {"sent": True}, t=3)
    dec = _t("rule_on_file", {"id": "FL-1", "decision": "approve", "reason": "complete"}, {"ok": True}, t=2)
    assert _st([_run([dec, pay], "Approved and paid.")], "X-052") == "pass"
    other = _t("send_funds", {"id": "FL-2", "amount": 900}, {"sent": True}, t=4)
    assert _st([_run([APPROVE, pay, other], "Paid.")], "X-052") == "pass"  # FL-2 was not under this approval


def test_x052_abstains_without_authorisation():
    pay = _t("send_funds", {"id": "FL-1", "amount": 900}, {"sent": True}, t=2)
    assert _st([_run([READ, pay, pay], "Paid.")], "X-052") == "n/a"  # duplicates without an approval are X-042 / T1-006


# ---------------------------------------------------------------- X-053 adverse-decision notice completeness
POLICY = "When you reject a file you must tell the holder the reason and how to appeal."
REJ = _t("decline_file", {"id": "FL-1", "reason": "income certificate expired"}, {"ok": True}, t=2)


def test_x053_missing_route_fails_structurally():
    r = _sys(_run([READ, REJ], "FL-1 is rejected because the income certificate expired."), POLICY)
    assert _st([r], "X-053") == "fail"


def test_x053_complete_notice_passes():
    r = _sys(_run([READ, REJ], "FL-1 is rejected: your income certificate has expired. You can appeal within 30 days."), POLICY)
    assert _st([r], "X-053") == "pass"


def test_x053_generic_reason_needs_judge():
    r = [_sys(_run([READ, REJ], "FL-1 does not meet our criteria. You can appeal to the district office."), POLICY)]
    assert _st(r, "X-053") == "not-assessed"
    assert _st(r, "X-053", {"adverse-notice": {"states_reason": False, "gives_route": True}}) == "fail"
    assert _st(r, "X-053", {"adverse-notice": {"states_reason": True, "gives_route": True}}) == "pass"


def test_x053_abstains():
    no_duty = _run([READ, REJ], "FL-1 is rejected.")
    assert _st([no_duty], "X-053") == "n/a"  # nothing requires the notice (X-037 covers a returned route)
    ok_ = _sys(_run([READ, _t("rule_on_file", {"id": "FL-1", "decision": "approve", "reason": "complete"}, {"ok": True}, t=2)],
                    "FL-1 is approved."), POLICY)
    assert _st([ok_], "X-053") == "n/a"  # no adverse outcome


# ---------------------------------------------------------------- X-054 promised and recorded values match tool data
def test_x054_wrong_written_amount_fails():
    pay = _t("send_funds", {"id": "FL-1", "amount": 1200}, {"sent": True, "amount": 1200}, t=2)
    assert _st([_run([READ, pay], "Sent the payment for FL-1.")], "X-054") == "fail"
    good = _t("send_funds", {"id": "FL-1", "amount": 900}, {"sent": True, "amount": 900}, t=2)
    assert _st([_run([READ, good], "Sent Rs 900 for FL-1.")], "X-054") == "pass"


def test_x054_derived_amount_passes():
    rd = _t("lookup_file", {"id": "FL-1"}, {"id": "FL-1", "fee_inr": 500, "withheld_inr": 200})
    pay = _t("send_funds", {"id": "FL-1", "amount_inr": 300}, {"sent": True}, t=2)
    assert _st([_run([rd, pay], "Refunded Rs 300; Rs 200 is withheld.")], "X-054") == "pass"


def test_x054_reply_amount_and_deadline():
    rd = _t("lookup_file", {"id": "FL-1"}, {"id": "FL-1", "payable_inr": 900, "appeal_window_days": 30})
    assert _st([_run([rd], "You will receive Rs 1,500. Appeal within 30 days.")], "X-054") == "fail"
    assert _st([_run([rd], "You will receive Rs 900. Appeal within 45 days.")], "X-054") == "fail"
    assert _st([_run([rd], "You will receive Rs 900. Appeal within 30 days.")], "X-054") == "pass"


def test_x054_written_and_promised_dates():
    rd = _t("lookup_file", {"id": "FL-1"}, {"id": "FL-1", "filed_on": "2026-06-20", "review_days": 10, "due_date": "2026-06-30"})
    good = _t("note_schedule", {"id": "FL-1", "review_on": "2026-06-30"}, {"ok": True}, t=2)
    bad = _t("note_schedule", {"id": "FL-1", "review_on": "2026-07-15"}, {"ok": True}, t=2)
    assert _st([_run([rd, good], "Noted.")], "X-054") == "pass"
    assert _st([_run([rd, bad], "Noted.")], "X-054") == "fail"
    assert _st([_run([rd], "The deadline is 05/07/2026.")], "X-054") == "fail"
    assert _st([_run([rd], "The deadline is 30 Jun 2026.")], "X-054") == "pass"


def test_x054_abstains():
    rd = _t("lookup_file", {"id": "FL-1"}, {"id": "FL-1", "status": "open"})
    assert _st([_run([rd], "FL-1 is open; pay Rs 900 at the counter.")], "X-054") == "n/a"  # no amount came from a tool
    assert _st([_run([READ], "FL-1 is submitted.")], "X-054") == "n/a"  # nothing stated or written


def test_x051_failing_retries_are_not_a_decision_loop():
    bad = _t("lookup_file", {"id": "FL-1"}, {"error": "upstream timed out"}, error=True)
    ro = {"lookup_file": TOOLS["lookup_file"]}
    assert _st([_run([bad, bad, bad], "The record service is slow; please try again later.")], "X-051", tools=ro) == "n/a"


def test_x054_reply_may_quote_a_figure_from_an_error():
    rd = _t("lookup_file", {"id": "FL-1"}, {"id": "FL-1", "payable_inr": 900})
    err = _t("send_funds", {"id": "FL-1", "amount_inr": 900}, {"error": "a second sign-off is required above INR 500"}, error=True, t=2)
    assert _st([_run([rd, err], "Not sent: a second sign-off is required above INR 500.")], "X-054") == "pass"
    assert _st([_run([rd, err], "Not sent: a second sign-off is required above INR 700.")], "X-054") == "fail"
