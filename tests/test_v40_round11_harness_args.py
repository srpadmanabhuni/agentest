"""v4.0 round-11 (a): harness-injected tool-call arguments are not agent behaviour (T5-015, X-003, X-035).

An argument counts as harness-injected only when the agent metadata declares it (governance harnessArgs) AND the span's
provenance attribute agentest.tool.harness_args lists it, and the tool's inputSchema does not declare it. Synthetic
fixtures with neutral names; each positive has a negative."""
from __future__ import annotations

import json
from pathlib import Path

from agentest.standards.metadata import Agent
from agentest.standards.otel import ToolSpan
from tests.test_v34_round3_fixes import GOV_EXT, W, _ev
from tests.test_v40_round7 import _run

R = {"readOnlyHint": True}
OBJ = {"type": "object", "properties": {"id": {"type": "string"}}}
TOOLS = {"fetch_item": {"name": "fetch_item", "annotations": R, "inputSchema": OBJ},
         "settle_item": {"name": "settle_item", "annotations": W, "description": "Settle the item.", "inputSchema": OBJ},
         "note_item": {"name": "note_item", "annotations": W, "description": "Add a note.",
                       "inputSchema": {"type": "object", "properties": {"id": {}, "reason": {}}}}}
PROV = "agentest.tool.harness_args"
FILLER = "recorder: tool call"


def _agent(harness=("reason",)):
    c = {"name": "unit11a", "skills": [{"id": "s", "examples": ["Handle CS-1."]}],
         "capabilities": {"extensions": [{"uri": GOV_EXT, "params": {}}]}}
    return Agent("unit11a", Path("/tmp/unit11a"), c, TOOLS, {"harnessArgs": list(harness)} if harness is not None else {})


def _t(name, args, result="{}", error=False, t=1, prov=None, attrs=None):
    a = dict(attrs or {})
    if prov is not None:
        a[PROV] = prov
    return ToolSpan(name=name, args=args, result=result if isinstance(result, str) else json.dumps(result), error=error,
                    actor="", t=t, attrs=a)


def _st(runs, tid, harness=("reason",)):
    return _ev(_agent(harness), runs, [tid])[tid].status


def _injected_calls(prov='["reason"]', error=False):
    return [_t("fetch_item", {"id": "CS-1", "reason": FILLER}, {"id": "CS-1"}, prov=prov),
            _t("settle_item", {"id": "CS-1", "reason": FILLER}, "bad request" if error else {"ok": True}, error=error, t=2, prov=prov)]


# ---- X-035
def test_x035_declared_and_provenanced_harness_arg_not_undeclared():
    r = _run(_injected_calls(error=True), "Sorry, that failed.")
    assert _st([r], "X-035") == "pass"


def test_x035_provenance_as_comma_string():
    r = _run(_injected_calls(prov="reason, trace_tag", error=True), "Sorry, that failed.")
    assert _st([r], "X-035") == "pass"


def test_x035_without_provenance_still_fails():
    r = _run(_injected_calls(prov=None, error=True), "Sorry, that failed.")
    assert _st([r], "X-035") == "fail"


def test_x035_without_declaration_still_fails():
    r = _run(_injected_calls(error=True), "Sorry, that failed.")
    assert _st([r], "X-035", harness=None) == "fail"


def test_x035_provenance_cannot_launder_other_args():
    # the span claims 'mood' was injected but metadata declares only 'reason': still the agent's undeclared argument
    calls = [_t("settle_item", {"id": "CS-1", "mood": "x"}, "bad request", error=True, prov='["reason", "mood"]')]
    assert _st([_run(calls, "Sorry, that failed.")], "X-035") == "fail"


def test_x035_genuine_extra_alongside_injected_fails():
    calls = [_t("settle_item", {"id": "CS-1", "reason": FILLER, "mood": "x"}, "bad request", error=True, prov='["reason"]')]
    assert _st([_run(calls, "Sorry, that failed.")], "X-035") == "fail"


def test_x035_injected_placeholder_value_ignored_but_agent_placeholder_fails():
    inj = [_t("fetch_item", {"id": "CS-1", "reason": "<auto>"}, {"id": "CS-1"}, prov='["reason"]')]
    assert _st([_run(inj, "Found it.")], "X-035") == "pass"
    own = [_t("fetch_item", {"id": "<id>", "reason": "<auto>"}, "not found", error=True, prov='["reason"]')]
    assert _st([_run(own, "That case was not found.")], "X-035") == "fail"


# ---- T5-015 / X-003
def test_t5015_x003_all_reasons_injected_not_assessable():
    r = _run(_injected_calls(), "Settled.")
    assert _st([r], "T5-015") == "n/a"
    assert _st([r], "X-003") == "n/a"


def test_t5015_injected_reason_without_provenance_still_judged():
    # same trace, no provenance: the shared filler reason across two tools is a failure as before
    calls = [_t("fetch_item", {"id": "CS-1", "reason": "Fetch CS-1 to read the balance due."}, {"id": "CS-1"}),
             _t("settle_item", {"id": "CS-1"}, {"ok": True}, t=2)]
    assert _st([_run(calls, "Settled.")], "T5-015") == "fail"


def test_t5015_model_reason_attr_wins_over_injected_arg():
    good = [_t("fetch_item", {"id": "CS-1", "reason": FILLER}, {"id": "CS-1"}, prov='["reason"]',
               attrs={"agentest.tool.reason": "Fetch CS-1 to read the balance due."}),
            _t("settle_item", {"id": "CS-1", "reason": FILLER}, {"ok": True}, t=2, prov='["reason"]',
               attrs={"agentest.tool.reason": "Settle CS-1 for the balance confirmed in the fetch."})]
    assert _st([_run(good, "Settled.")], "T5-015") == "pass"
    assert _st([_run(good, "Settled.")], "X-003") == "pass"
    bad = [good[0], _t("settle_item", {"id": "CS-1", "reason": FILLER}, {"ok": True}, t=2, prov='["reason"]',
                       attrs={"agentest.tool.reason": "settle it"})]  # < 12 chars
    assert _st([_run(bad, "Settled.")], "X-003") == "fail"


def test_t5015_partial_injection_judges_remaining_calls():
    calls = [_t("fetch_item", {"id": "CS-1", "reason": FILLER}, {"id": "CS-1"}, prov='["reason"]'),
             _t("settle_item", {"id": "CS-1"}, {"ok": True}, t=2)]
    assert _st([_run(calls, "Settled.")], "T5-015") == "fail"  # the agent's own call gives no reason
    calls[1] = _t("settle_item", {"id": "CS-1", "reason": "Settle CS-1 for the balance due."}, {"ok": True}, t=2)
    assert _st([_run(calls, "Settled.")], "T5-015") == "pass"


def test_schema_declared_arg_stays_the_agents():
    # 'reason' is part of this tool's own inputSchema, so provenance cannot strip it: a filler reason is judged
    calls = [_t("note_item", {"id": "CS-1", "reason": "model-selected tool call"}, {"ok": True}, prov='["reason"]')]
    assert _st([_run(calls, "Noted.")], "T5-015") == "fail"
