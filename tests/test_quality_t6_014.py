"""Regression cases for requests after a failed tool call."""

import pytest

from tests.test_rai_additions_rules import W, _agent, _run, _st, _tool


@pytest.mark.parametrize(("answer", "expected"), [
    ("Could you send me your email and the day once more?", "fail"),
    ("Can you share the day again?", "fail"),
    ("Can you share your name? Could you send me your email again?", "fail"),
    ("What day and email should I use?", "fail"),
    ("Could you send me your room number?", "pass"),
    ("Could you send me your receipt? I still have your email.", "pass"),
    ("Could you send me a reminder by email?", "pass"),
])
def test_context_after_booking_failure(answer, expected):
    agent = _agent({"book_slot": {"name": "book_slot", "annotations": W}})
    first = _run(
        input="Book a slot for dana@example.invalid on Friday.",
        answer="The booking service failed.",
        tools=[_tool("book_slot", args={"email": "dana@example.invalid", "day": "Friday"},
                     result='{"error":"503"}', error=True)],
        input_id="t0", conversation="c1", t0=1,
    )
    second = _run(input="Try again please", answer=answer, input_id="t1", conversation="c1", t0=2)
    assert _st(agent, [first, second], "T6-014") == expected
