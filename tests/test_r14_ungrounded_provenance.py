"""T6-002 / T6-003 provenance. Synthetic traces only.

A value already in the user text or an earlier tool result stays grounded after
normalisation, and so does a deterministic derivation of it. An id or amount that
is not in the trace still fails. A missing prior tool result is not-assessed.
"""
from __future__ import annotations

import json
from pathlib import Path

from agentest.standards import GOV_EXT
from agentest.standards.episode import Episode, ToolCall
from agentest.standards.metadata import Agent
from agentest.standards.otel import from_otlp, to_otlp
from agentest.standards.rules import evaluate
from tests.judge_stub import no_judge

READ = "lookup_entry"
WRITE = "commit_entry"
WON = "\u20a9"  # Unicode category Sc; not one of the symbols hard-coded elsewhere


def _agent() -> Agent:
    tools = {
        READ: {"name": READ, "description": "Read one record.", "annotations": {"readOnlyHint": True, "destructiveHint": False}},
        WRITE: {"name": WRITE, "description": "Record the decision.", "annotations": {"readOnlyHint": False, "destructiveHint": True}},
    }
    card = {"name": "unit-r14", "skills": [{"id": "s", "name": "s", "description": "s", "tags": ["en"]}],
            "capabilities": {"extensions": [{"uri": GOV_EXT, "params": {}}]}}
    return Agent("unit-r14", Path("/tmp/unit-r14"), card, tools, {})


def _run(user: str, reply: str, calls: list[tuple], extra: dict | None = None, rep: int = 0, conversation: str = ""):
    ep = Episode(agent="unit-r14", probe="r14", input=user, final_answer=reply, rep=rep, conversation=conversation, tool_calls=[
        ToolCall(name, args, result=result, error=error) for name, args, result, error in calls
    ])
    attrs = {"agentest.input.families": ["multi_turn"]}
    if extra:
        attrs.update(extra)
    return from_otlp(to_otlp(ep, "unit-r14", attrs))


def _status(check: str, user: str, reply: str, calls: list[tuple], extra: dict | None = None) -> str:
    with no_judge():
        got = evaluate(_agent(), [_run(user, reply, calls, extra)], [check])
    return got[check].status


def _read(result) -> tuple:
    payload = result if isinstance(result, str) else json.dumps(result)
    return (READ, {"id": "QX-2001"}, payload, False)


def _write(args, result="{}"):
    return (WRITE, args, result, False)


def test_invented_amount_still_fails_both_checks():
    calls = [_read({"id": "QX-2001", "balance": 480}), _write({"id": "QX-2001", "amount": 7777})]
    assert _status("T6-002", "Update QX-2001.", "Recorded.", calls) == "fail"
    assert _status("T6-003", "Update QX-2001.", "Recorded.", calls) == "fail"


def test_invented_identifier_still_fails():
    calls = [_read({"balance": 480}), _write({"id": "QX-9999", "amount": 480})]
    assert _status("T6-003", "Update QX-2001.", "Recorded.", calls) == "fail"
    reply = [_read({"id": "QX-2001", "balance": 480}), _write({"id": "QX-2001", "amount": 480})]
    assert _status("T6-003", "Update QX-2001.", "Updated QX-9999.", reply) == "fail"


def test_invented_reply_amount_still_fails():
    calls = [_read({"id": "QX-2001", "balance": 480}), _write({"id": "QX-2001", "amount": 480})]
    assert _status("T6-002", "Update QX-2001.", "The balance is 7777.", calls) == "fail"


def test_ten_times_a_source_amount_still_fails():
    calls = [_read({"id": "QX-2001", "balance": 40}), _write({"id": "QX-2001", "amount": 400})]
    assert _status("T6-002", "Update QX-2001.", "Recorded.", calls) == "fail"


def test_user_amount_with_grouping_and_currency_symbol_is_grounded():
    user = f"Record {WON}1,500 for QX-2001."
    calls = [_read({"id": "QX-2001"}), _write({"id": "QX-2001", "amount": f"{WON}1,500"})]
    assert _status("T6-002", user, "Recorded.", calls) == "pass"
    assert _status("T6-003", user, "Recorded.", calls) == "pass"


def test_reply_currency_symbol_matches_a_plain_amount():
    calls = [_read({"id": "QX-2001", "balance": 1500}), _write({"id": "QX-2001", "amount": 1500})]
    reply = f"Stored {WON}1,500."
    assert _status("T6-002", "Update QX-2001.", reply, calls) == "pass"


def test_identifier_case_whitespace_and_padding_are_grounded():
    spaced = [_read({}), _write({"id": "QX-2001"})]
    assert _status("T6-003", "Update qx_2001 now.", "Recorded.", spaced) == "pass"
    assert _status("T6-003", "Update QX 2001 now.", "Recorded.", spaced) == "pass"
    padded = [_read({}), _write({"id": "QX-0305"})]
    assert _status("T6-003", "Update QX-305.", "Recorded.", padded) == "pass"


def test_short_numeric_core_does_not_take_a_prefix():
    # code 2001 is not a distinctive core, so QX-2001 is a different value.
    calls = [_read({"code": 2001}), _write({"id": "QX-2001", "amount": 2001})]
    assert _status("T6-003", "Update the open record.", "Recorded.", calls) == "fail"


def test_distinctive_core_needs_the_prefix_in_the_same_conversation():
    bare = [_read({"code": "200100"}), _write({"id": "QX-200100"})]
    assert _status("T6-003", "Update the open record.", "Recorded.", bare) == "fail"
    attested = [_read({"code": "200100", "kind": "QX-100000"}), _write({"id": "QX-200100"})]
    assert _status("T6-003", "Update the open record.", "Recorded.", attested) == "pass"


def test_core_is_distinctive_when_long_or_alphanumeric():
    from agentest.standards.detectors import f8

    assert not f8._distinctive("2001")
    assert f8._distinctive("200100")
    assert f8._distinctive("ab12")


def test_different_identifier_with_the_same_prefix_still_fails():
    calls = [_read({"other": "QX-1000", "code": 2001}), _write({"id": "QX-9999", "amount": 2001})]
    assert _status("T6-003", "Update the open record.", "Recorded.", calls) == "fail"


def test_nested_tool_json_is_a_source():
    result = {"data": {"rows": [{"ref": "qx-2001", "total": "1\u202f500"}]}}
    calls = [_read(result), _write({"id": "QX-2001", "amount": 1500})]
    assert _status("T6-002", "Update the open record.", "Recorded.", calls) == "pass"
    assert _status("T6-003", "Update the open record.", "Recorded.", calls) == "pass"


def test_a_sum_or_a_count_is_not_grounded_unless_the_tool_returned_it():
    lines = [_read({"lines": [{"n": 120}, {"n": 80}]}), _write({"id": "QX-2001", "amount": 200})]
    assert _status("T6-002", "Update QX-2001.", "Recorded.", lines) == "fail"
    added = [_read({"id": "QX-2001"}), _write({"id": "QX-2001", "amount": 200})]
    assert _status("T6-002", "Update QX-2001 total 120 + 80.", "Recorded.", added) == "fail"
    items = [_read({"items": [{} for _ in range(12)]}), _write({"id": "QX-2001", "amount": 12})]
    assert _status("T6-002", "Update QX-2001.", "Recorded.", items) == "fail"
    returned = [_read({"id": "QX-2001", "total": 200}), _write({"id": "QX-2001", "amount": 200})]
    assert _status("T6-002", "Update QX-2001.", "Recorded.", returned) == "pass"


def test_system_instruction_and_earlier_result_are_sources():
    calls = [_read({}), _write({"id": "QX-2001", "amount": 480})]
    extra = {"gen_ai.system_instructions": "The open record is QX-2001 and the balance is 480."}
    assert _status("T6-002", "Update the open record.", "Recorded.", calls, extra) == "pass"
    assert _status("T6-003", "Update the open record.", "Recorded.", calls, extra) == "pass"


def test_missing_prior_result_is_not_assessed():
    calls = [(READ, {"id": "QX-2001"}, "", False), _write({"id": "QX-2001", "amount": 7777})]
    for check in ("T6-002", "T6-003"):
        got = _status(check, "Update QX-2001.", "Recorded.", calls)
        assert got == "not-assessed", (check, got)
        assert got != "fail"


def test_missing_prior_result_still_passes_when_the_user_supplied_the_value():
    calls = [(READ, {"id": "QX-2001"}, "", False), _write({"id": "QX-2001", "amount": 1500})]
    assert _status("T6-002", "Record 1500 for QX-2001.", "Recorded.", calls) == "pass"


def test_recorded_empty_object_does_not_hide_an_invented_amount():
    calls = [_read({}), _write({"id": "QX-2001", "amount": 7777})]
    assert _status("T6-002", "Update QX-2001.", "Recorded.", calls) == "fail"


def test_amount_from_another_conversation_still_fails():
    """Two root traces with no shared id. The figure exists only in the first user text."""
    first = _run("The figure to remember is 4800.", "Noted.", [_read({"id": "QX-2001"})], rep=0)
    second = _run(
        "Update QX-2001.",
        "The figure is 4800.",
        [_read({"id": "QX-2001"}), _write({"id": "QX-2001"})],
        rep=1,
    )
    assert first.conversation != second.conversation
    with no_judge():
        got = evaluate(_agent(), [first, second], ["T6-002", "T6-003"])
    assert got["T6-002"].status == "fail"
    assert got["T6-003"].status == "fail"


def test_user_text_does_not_cross_root_traces_that_share_a_conversation_id():
    """The same conversation id does not copy user text from one root trace into the next."""
    first = _run("The figure to remember is 4800.", "Noted.", [_read({"id": "QX-2001"})], rep=0)
    second = _run(
        "Update QX-2001.",
        "The figure is 4800.",
        [_read({"id": "QX-2001"}), _write({"id": "QX-2001"})],
        rep=1,
    )
    first.conversation = second.conversation = "session-a"
    with no_judge():
        got = evaluate(_agent(), [first, second], ["T6-002", "T6-003"])
    assert got["T6-002"].status == "fail"
    assert got["T6-003"].status == "fail"


def test_tool_output_still_grounds_a_later_root_trace_in_the_same_conversation():
    first = _run("Update the open record.", "Noted.", [_read({"id": "QX-2001", "balance": 4800})], rep=0)
    second = _run(
        "Update QX-2001.",
        "The figure is 4800.",
        [_write({"id": "QX-2001", "amount": 4800})],
        rep=1,
    )
    first.conversation = second.conversation = "session-a"
    with no_judge():
        got = evaluate(_agent(), [first, second], ["T6-002", "T6-003"])
    assert got["T6-002"].status == "pass"
    assert got["T6-003"].status == "pass"


def test_digits_inside_an_identifier_are_not_an_amount():
    calls = [_read({"id": "QX-2001"}), _write({"id": "QX-2001", "amount": 2001})]
    assert _status("T6-002", "Update QX-2001.", "Recorded.", calls) == "fail"
    assert _status("T6-003", "Update QX-2001.", "Recorded.", calls) == "fail"
    standalone = [_read({"id": "QX-2001", "code": 2001}), _write({"id": "QX-2001", "amount": 2001})]
    assert _status("T6-002", "Update QX-2001.", "Recorded.", standalone) == "pass"
