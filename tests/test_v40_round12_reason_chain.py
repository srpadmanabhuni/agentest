"""v4.0 r12 (5 Nov): T5-015 / X-003 - one decision's reason carried along its own hand-off chain is not a template.

A reason shared by different tools stays a template unless, in every run where it appears, it is on a state-changing
call, every read-only call carrying it is a hand-off (the next tool call comes from a different agent), and the chain
crosses an agent boundary. Synthetic fixtures with neutral names; each positive has a negative."""
from __future__ import annotations

import json
from pathlib import Path

from agentest.standards.metadata import Agent
from agentest.standards.otel import ToolSpan
from tests.test_v34_round3_fixes import GOV_EXT, W, _ev
from tests.test_v40_round7 import _run

R = {"readOnlyHint": True}
TOOLS = {"fetch_item": {"name": "fetch_item", "annotations": R},
         "pass_to_signer": {"name": "pass_to_signer", "annotations": R},
         "note_item_outcome": {"name": "note_item_outcome", "annotations": W, "description": "Record the outcome."},
         "signer_ok": {"name": "signer_ok", "annotations": W, "description": "Sign off the outcome."},
         "settle_item": {"name": "settle_item", "annotations": W, "description": "Settle the item."}}
WHY = "CS-1 balance of 700 is due under clause 4; the note shows no hold."


def _agent():
    c = {"name": "unit12r", "skills": [{"id": "s", "examples": ["Handle CS-1."]}],
         "capabilities": {"extensions": [{"uri": GOV_EXT, "params": {}}]}}
    return Agent("unit12r", Path("/tmp/unit12r"), c, TOOLS, {})


def _t(name, reason, agent, t):
    return ToolSpan(name=name, args={"id": "CS-1", "reason": reason}, result=json.dumps({"ok": True}), error=False,
                    actor=agent, t=t, agent=agent)


def _st(calls, tid="T5-015"):
    return _ev(_agent(), [_run(calls, "Settled CS-1.")], [tid])[tid].status


def _chain(why_fetch="Read CS-1 to see the balance due.", why_settle=WHY, settle_agent="payer"):
    return [_t("fetch_item", why_fetch, "checker", 1), _t("note_item_outcome", WHY, "checker", 2),
            _t("pass_to_signer", WHY, "checker", 3), _t("signer_ok", WHY, "signer", 4),
            _t("settle_item", why_settle, settle_agent, 5)]


def test_decision_reason_carried_through_handoffs_passes():
    assert _st(_chain()) == "pass"
    assert _st(_chain(), "X-003") == "pass"


def test_record_then_handoff_same_agent_passes():
    calls = [_t("fetch_item", "Read CS-1 to see the balance due.", "checker", 1), _t("note_item_outcome", WHY, "checker", 2),
             _t("pass_to_signer", WHY, "checker", 3), _t("signer_ok", "Sign-off: the recorded 700 matches clause 4.", "signer", 4)]
    assert _st(calls) == "pass"


def test_reason_also_on_an_ordinary_read_is_a_template():
    assert _st(_chain(why_fetch=WHY, why_settle="Pay the signed-off 700 for CS-1.")) == "fail"  # the lookup reuses the decision reason: not about that call


def test_reason_on_reads_only_is_a_template():
    calls = [_t("fetch_item", WHY, "checker", 1), _t("pass_to_signer", WHY, "checker", 2), _t("signer_ok", "Sign-off for CS-1 at 700.", "signer", 3)]
    assert _st(calls) == "fail"


def test_reason_reused_by_two_writes_of_one_agent_is_a_template():
    calls = [_t("fetch_item", "Read CS-1 to see the balance due.", "checker", 1), _t("note_item_outcome", WHY, "checker", 2),
             _t("settle_item", WHY, "checker", 3)]
    assert _st(calls) == "fail"


def test_no_agent_identity_keeps_the_old_rule():
    calls = [ToolSpan(name=n, args={"id": "CS-1", "reason": WHY}, result="{}", error=False, actor="", t=i)
             for i, n in enumerate(["note_item_outcome", "pass_to_signer", "signer_ok"], 1)]
    calls.append(ToolSpan(name="settle_item", args={"id": "CS-1", "reason": "Pay the signed-off 700 for CS-1."}, result="{}",
                          error=False, actor="", t=4))
    assert _st(calls) == "fail"


def test_missing_reason_still_fails():
    calls = _chain()
    calls[2] = ToolSpan(name="pass_to_signer", args={"id": "CS-1"}, result="{}", error=False, actor="checker", t=3, agent="checker")
    assert _st(calls) == "fail"
