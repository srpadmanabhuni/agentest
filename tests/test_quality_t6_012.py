"""T6-012 should use the previous write when a correction omits the old value."""

import pytest

from tests.test_rai_additions_rules import W, _agent, _run, _st, _tool

AGENT = _agent({"book_slot": {"name": "book_slot", "annotations": W}})


def booking(turn, text, **args):
    return _run(input=text, input_id=str(turn), conversation="booking", t0=turn,
                tools=[_tool("book_slot", args=args, result="{}")])


@pytest.mark.parametrize(("day", "verdict"), [
    ("tuesday", "fail"),
    ("wednesday", "fail"),
    ("friday", "pass"),
])
def test_implicit_correction(day, verdict):
    first = booking(1, "Book a slot for Tuesday", day="tuesday", room="B")
    corrected = booking(2, "Actually, Friday please.", day=day, room="B")
    assert _st(AGENT, [first, corrected], "T6-012") == verdict


def test_no_previous_write():
    assert _st(AGENT, [booking(1, "Actually, Friday please.", day="tuesday")], "T6-012") == "n/a"


def test_ambiguous_previous_write():
    first = booking(1, "Book Tuesday to Thursday", start="tuesday", end="thursday")
    corrected = booking(2, "Actually, Friday please.", start="tuesday", end="thursday")
    assert _st(AGENT, [first, corrected], "T6-012") == "n/a"


def test_second_correction_supersedes_first():
    runs = [booking(1, "Book Tuesday", day="tuesday"),
            booking(2, "Actually, Friday please.", day="friday"),
            booking(3, "Actually, Monday please.", day="monday")]
    assert _st(AGENT, runs, "T6-012") == "pass"

def test_correction_before_later_write():
    first = booking(1, "Book a slot for Tuesday", day="tuesday")
    corrected = _run(input="Actually, Friday please.", input_id="2", conversation="booking", t0=2)
    later = booking(3, "Go ahead", day="tuesday")
    assert _st(AGENT, [first, corrected, later], "T6-012") == "fail"


def test_explicit_old_value_needs_no_previous_write():
    corrected = _run(input="Friday, not Tuesday", tools=[_tool("book_slot", args={"day": "tuesday"})])
    assert _st(AGENT, [corrected], "T6-012") == "fail"
