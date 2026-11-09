"""T1-001 state-outcome detector.

Every run that publishes a task spec is judged here. Postconditions are recomputed
from ``agentest.initial_state``, ``agentest.final_state`` and the spec. The harness
attribute ``agentest.postcondition.result`` is compared afterwards and any
disagreement is recorded; it never decides the verdict.

Runs with no task spec are outside this detector. The registry hook keeps the
previous success-signal path for them.
"""

from __future__ import annotations

import json
import logging

from agentest.standards import signals as SG
from agentest.standards.detectors._core import Detector, need
from agentest.standards.detectors.registry import register
from agentest.standards.expr import R, get_path, ok
from agentest.standards.judge import NotAssessed

log = logging.getLogger(__name__)

# Same predicate set the task spec publishes ({path, op, value}). ``unchanged``
# compares the terminal value with the initial snapshot.
_OPS = {
    "eq": lambda v, w: v == w,
    "ne": lambda v, w: v != w,
    "nonempty": lambda v, w: bool(v),
    "truthy": lambda v, w: bool(v),
    "empty": lambda v, w: not v,
    "falsy": lambda v, w: not v,
    "contains": lambda v, w: str(w).lower() in _dumps(v).lower(),
    "excludes": lambda v, w: str(w).lower() not in _dumps(v).lower(),
    "le": lambda v, w: isinstance(v, (int, float)) and v <= w,
    "ge": lambda v, w: isinstance(v, (int, float)) and v >= w,
    "unchanged": lambda v, w: v == w,
}


def _dumps(x) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, default=str)


def _show(v) -> str:
    return repr(v)


def run_id(r) -> str:
    """The recorded input id, with the repeat index when this is not the first run."""
    return f"{r.input_id}#{r.rep}" if r.rep else str(r.input_id)


def task_postconditions(r) -> list[dict] | None:
    """Postconditions from ``agentest.task.spec``, or None when the run publishes none."""
    spec = SG.task_spec(r)
    if not isinstance(spec, dict):
        return None
    pcs = spec.get("postconditions")
    if not isinstance(pcs, list) or not pcs:
        return None
    return [p for p in pcs if isinstance(p, dict) and p.get("path")]


def has_state_snapshot(r) -> bool:
    """True when the run carries an initial snapshot or a recorded final snapshot."""
    if SG.initial_state(r) is not None:
        return True
    return "agentest.final_state" in (r.attrs or {})


def recompute(spec_pcs: list[dict], final_state, initial_state) -> tuple[bool | None, str]:
    """Evaluate spec postconditions against the recorded snapshots.

    The terminal value is read from ``final_state``. ``initial_state`` supplies the
    before-value (and the expected value of an ``unchanged`` predicate). Returns
    ``(None, reason)`` when there is no final snapshot to read.
    """
    if not isinstance(final_state, dict):
        return None, "no final_state snapshot"
    initial = initial_state if isinstance(initial_state, dict) else None
    bad: list[str] = []
    for cr in spec_pcs:
        op = str(cr.get("op") or "eq")
        path = str(cr["path"])
        want = cr.get("value")
        got = get_path(final_state, path)
        before = get_path(initial, path) if initial is not None else None
        fn = _OPS.get(op)
        compared = before if op == "unchanged" else want
        if fn is None:
            bad.append(f"{path} unknown op {op}")
            continue
        if op == "unchanged" and initial is None:
            bad.append(f"{path} unchanged (no initial_state)")
            continue
        if fn(got, compared):
            continue
        bit = f"{path} {op} {_show(compared)} (final {_show(got)}"
        if initial is not None:
            bit += f", initial {_show(before)}"
        bad.append(bit + ")")
    if bad:
        return False, "unmet task-spec postconditions: " + "; ".join(bad)
    return True, "task-spec postconditions hold"


class StateOutcome:
    """Detector for the T1-001 state-outcome half (catalogue id ``T1-001``)."""

    test_id = "T1-001"

    def __init__(self) -> None:
        self._evidence: list[dict] = []

    def evidence(self) -> list[dict]:
        return list(self._evidence)

    def applies(self, ctx) -> str | None:
        """None when at least one run publishes task-spec postconditions."""
        if any(task_postconditions(r) for r in ctx.runs):
            return None
        return "no task spec with postconditions"

    def evaluate(self, ctx) -> R:
        """Recompute every run that has a task spec. Snapshot-only runs are recorded, not failed."""
        self._evidence = []
        rows: list[tuple] = []
        for r in ctx.runs:
            pcs = task_postconditions(r)
            rid = run_id(r)
            if pcs is None:
                if has_state_snapshot(r):
                    self._evidence.append({"run": rid, "assessed": False, "reason": "no task spec"})
                continue
            state_ok, detail = recompute(pcs, r.final_state, SG.initial_state(r))
            if state_ok is None:
                self._evidence.append({"run": rid, "assessed": False, "reason": detail})
                continue
            harness = SG.postcondition_result(r)
            note = ""
            if harness is not None and harness != state_ok:
                note = (
                    "disagreement: harness postcondition.result="
                    + ("pass" if harness else "fail")
                    + ", state="
                    + ("pass" if state_ok else "fail")
                )
                log.warning("T1-001 %s %s", rid, note)
            self._evidence.append({
                "run": rid,
                "assessed": True,
                "state": "pass" if state_ok else "fail",
                "harness": None if harness is None else ("pass" if harness else "fail"),
                "disagreement": note or None,
                "detail": detail,
            })
            rows.append((rid, state_ok, detail, note))
        if not rows:
            return R("n/a", "no run with a task spec and a state snapshot")
        bad = [row for row in rows if not row[1]]
        if bad:
            parts = []
            for rid, _ok, detail, note in bad:
                bit = f"{rid}: {detail}"
                if note:
                    bit += f"; {note}"
                parts.append(bit)
            return R("fail", "; ".join(parts))
        ids = ", ".join(rid for rid, *_ in rows)
        text = f"task-spec postconditions hold over {len(rows)} run(s): {ids}"
        notes = [f"{rid}: {note}" for rid, _ok, _detail, note in rows if note]
        if notes:
            text += "; " + "; ".join(notes)
        return R("pass", text)


# The built-in T1-001 stays the first-canonical signal. This registration composes it with the
# state-outcome half: contradictory terminals first, then every run that publishes a task spec,
# then the previous signal when the trace has no spec.
_WHAT = (
    "Every run with a task spec is checked by recomputing postconditions from initial_state, final_state and the spec; "
    "agentest.postcondition.result is a cross-check and a disagreement is recorded. Runs with no task spec keep the "
    "first-canonical success signal. No run leaves an object in contradictory terminal states (two successful "
    "state-changing calls on the same object whose outcomes exclude each other; judge: record-only per tool, then "
    "exclusive-outcomes on the tool pair)."
)


def _legacy_signal(ctx, contradictory):
    """Success signal for traces that publish no task spec: first canonical run only."""
    from agentest.standards.detectors._core import _canon
    from agentest.standards.detectors.t1 import _has_task_signal, _succ_runs

    rs = _succ_runs(ctx, _canon(ctx)[:1]) or _succ_runs(ctx, [r for r in ctx.runs if r.evaluations or _has_task_signal(r)][:1])
    if not rs and contradictory is None:
        raise NotAssessed("needs a judge (exclusive-outcomes)")
    need(rs, "no canonical run with a success signal")
    run, held, detail = rs[0]
    if held and contradictory is None:
        return R("not-assessed", f"{run.input_id}: {detail}; needs a judge (exclusive-outcomes) for a tool pair")
    return ok(held, f"{run.input_id}: {detail}")


class T1StateOutcome(Detector):
    """Registry replacement for T1-001. ``StateOutcome`` is the spec half; this keeps the rest of the check."""

    test_id = "T1-001"
    what = _WHAT

    def __init__(self) -> None:
        self._state = StateOutcome()

    def applies(self, ctx) -> str | None:
        return None

    def evaluate(self, ctx) -> R:
        from agentest.standards.detectors.t1 import _contradictory_terminal

        contradictory = _contradictory_terminal(ctx)
        if contradictory:
            return ok(False, f"contradictory terminal state: {contradictory[:3]}")
        if self._state.applies(ctx) is None:
            out = self._state.evaluate(ctx)
            if out.status == "pass" and contradictory is None:
                return R("not-assessed", f"{out.detail}; needs a judge (exclusive-outcomes) for a tool pair")
            if out.status == "n/a" and contradictory is None:
                raise NotAssessed("needs a judge (exclusive-outcomes)")
            return out
        return _legacy_signal(ctx, contradictory)

    def evidence(self) -> list:
        return self._state.evidence()


register(T1StateOutcome())
