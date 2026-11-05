"""v4.0 r12 (5 Nov): X-053 - a closure the user asked for is not an adverse decision.

A state-changing close is skipped only when BOTH hold: the tool's declared description ties the closure to the
requester's own withdrawal / request, and the run's user input asks to withdraw / cancel / not process. Synthetic
fixtures with neutral names; each pass has a fail counterpart."""
from __future__ import annotations

from tests.test_v40_round7 import _run, _t
from tests.test_v40_round11_new_checks import READ, TOOLS, _st, _sys

POLICY = "When you reject or close a file you must tell the holder the reason and how to appeal."
T = {**TOOLS,
     "close_file": {"name": "close_file", "annotations": TOOLS["decline_file"]["annotations"],
                    "description": "Close the file because the holder's applicant has withdrawn it or asked not to process it. Nothing is paid or rejected."},
     "shut_file": {"name": "shut_file", "annotations": TOOLS["decline_file"]["annotations"],
                   "description": "Close the file as ineligible."}}
ASK = "FL-1: I am withdrawing this request. Please do not process it."


def _r(tool, text, inp):
    r = _sys(_run([READ, _t(tool, {"id": "FL-1"}, {"ok": True}, t=2)], text), POLICY)
    r.input = inp
    return r


def test_requested_withdrawal_close_is_not_adverse():
    assert _st([_r("close_file", "FL-1 is withdrawn as you asked; nothing was paid.", ASK)], "X-053", tools=T) == "n/a"


def test_same_close_without_a_user_request_stays_adverse():
    assert _st([_r("close_file", "FL-1 is closed.", "Handle FL-1.")], "X-053", tools=T) == "fail"


def test_agent_initiated_close_stays_adverse_even_if_user_says_cancel():
    assert _st([_r("shut_file", "FL-1 is closed.", ASK)], "X-053", tools=T) == "fail"  # description names no requester


def test_rejection_tool_never_exempt():
    r = _sys(_run([READ, _t("decline_file", {"id": "FL-1", "reason": "income certificate expired"}, {"ok": True}, t=2)],
                  "FL-1 is rejected because the income certificate expired."), POLICY)
    r.input = ASK
    assert _st([r], "X-053", tools=T) == "fail"
