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
from agentest.standards.expr import R

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


# Leaves of the computed ``effects.<object>.*`` view. Anything else under ``effects.``
# is a path this checker cannot resolve.
_EFFECT_METRICS = ("new_payouts", "paid_inr", "new_rejections")


def _as_map(bucket) -> dict:
    """A payout or rejection collection as a map of record id to record."""
    if isinstance(bucket, dict):
        return {str(k): v for k, v in bucket.items() if isinstance(v, dict)}
    if isinstance(bucket, list):
        out = {}
        for i, rec in enumerate(bucket):
            if not isinstance(rec, dict):
                continue
            key = next((str(rec[k]) for k in ("reference", "id") if isinstance(rec.get(k), str) and rec.get(k)), str(i))
            out[key] = rec
        return out
    return {}


def _collection(state, name: str) -> dict:
    """The named collection on the snapshot: under ``output`` when that object is present, else at the root."""
    if not isinstance(state, dict):
        return {}
    output = state.get("output")
    if isinstance(output, dict) and name in output:
        return _as_map(output.get(name))
    if name in state:
        return _as_map(state.get(name))
    return {}


def _object_ids(key: str, rec: dict) -> list[str]:
    """Subject ids named by the record (any ``*_id`` / ``id`` field). The record key is the fallback."""
    ids: list[str] = []
    for fk, fv in rec.items():
        if isinstance(fv, str) and fv and (fk == "id" or fk.endswith("_id")) and fv not in ids:
            ids.append(fv)
    if not ids and key:
        ids.append(key)
    return ids


def _amount(rec: dict):
    """Money on one payout record. Prefer an INR amount field; otherwise any numeric amount."""
    for fk in ("amount_inr", "paid_inr", "amount"):
        fv = rec.get(fk)
        if isinstance(fv, (int, float)) and not isinstance(fv, bool):
            return fv
    for fk, fv in rec.items():
        if isinstance(fv, (int, float)) and not isinstance(fv, bool) and ("amount" in fk.lower() or fk.lower().endswith("_inr")):
            return fv
    return 0


def _new_records(initial, final, name: str) -> list[tuple[str, dict]]:
    """Records present in the final collection and absent from the initial one, keyed by record id."""
    before = _collection(initial, name)
    after = _collection(final, name)
    return [(k, rec) for k, rec in after.items() if k not in before]


def effects_view(initial, final) -> dict[str, dict]:
    """``effects.<object>`` computed from the snapshot change.

    Per subject id: how many payout records appeared, the amount paid on those
    records, and how many rejection records appeared. Collections are the
    generic ``payouts`` and ``rejections`` maps. A subject id is whatever
    ``*_id`` field the record carries.
    """
    view: dict[str, dict] = {}

    def row(oid: str) -> dict:
        return view.setdefault(oid, {"new_payouts": 0, "paid_inr": 0, "new_rejections": 0})

    for key, rec in _new_records(initial, final, "payouts"):
        amt = _amount(rec)
        for oid in _object_ids(key, rec):
            item = row(oid)
            item["new_payouts"] += 1
            item["paid_inr"] += amt
    for key, rec in _new_records(initial, final, "rejections"):
        for oid in _object_ids(key, rec):
            row(oid)["new_rejections"] += 1
    for item in view.values():
        paid = item["paid_inr"]
        if isinstance(paid, float) and paid.is_integer():
            item["paid_inr"] = int(paid)
    return view


def _path_in(state, path: str) -> tuple[bool, object]:
    """Whether ``path`` is present. A missing segment is unresolved; an explicit null is a value."""
    cur = state
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.lstrip("-").isdigit():
            i = int(part)
            if -len(cur) <= i < len(cur):
                cur = cur[i]
            else:
                return False, None
        else:
            return False, None
    return True, cur


def _resolve(path: str, final_state, initial, view: dict) -> tuple[bool, object, object]:
    """``(resolved, final value, initial value)``. Effects metrics are always resolved (0 when the object is absent)."""
    if path.startswith("effects."):
        obj, sep, metric = path[len("effects."):].rpartition(".")
        if not sep or not obj or metric not in _EFFECT_METRICS:
            return False, None, None
        final_row = view.get(obj) or {m: 0 for m in _EFFECT_METRICS}
        # The metric is the change itself, so its value on the initial snapshot is 0.
        return True, final_row[metric], 0
    ok_final, got = _path_in(final_state, path)
    if not ok_final:
        return False, None, None
    before = _path_in(initial, path)[1] if isinstance(initial, dict) else None
    return True, got, before


def recompute(spec_pcs: list[dict], final_state, initial_state) -> tuple[str, str]:
    """Evaluate spec postconditions against the recorded snapshots.

    Returns ``(pass|fail|not-assessed|n/a, detail)``. An ``effects.<object>`` metric is
    computed from the change between the two snapshots. A path that is neither that
    metric nor present in the final snapshot is not assessed, and is not a failure.
    """
    if not isinstance(final_state, dict):
        return "n/a", "no final_state snapshot"
    initial = initial_state if isinstance(initial_state, dict) else None
    view = effects_view(initial, final_state)
    bad: list[str] = []
    unresolved: list[str] = []
    for cr in spec_pcs:
        op = str(cr.get("op") or "eq")
        path = str(cr["path"])
        want = cr.get("value")
        resolved, got, before = _resolve(path, final_state, initial, view)
        if not resolved:
            unresolved.append(path)
            continue
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
        return "fail", "unmet task-spec postconditions: " + "; ".join(bad)
    if unresolved:
        return "not-assessed", "unresolved postcondition path: " + ", ".join(unresolved)
    return "pass", "task-spec postconditions hold"


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
            status, detail = recompute(pcs, r.final_state, SG.initial_state(r))
            if status == "n/a":
                self._evidence.append({"run": rid, "assessed": False, "reason": detail})
                continue
            harness = SG.postcondition_result(r)
            note = ""
            if status in ("pass", "fail") and harness is not None and harness != (status == "pass"):
                note = (
                    "disagreement: harness postcondition.result="
                    + ("pass" if harness else "fail")
                    + ", state="
                    + status
                )
                log.warning("T1-001 %s %s", rid, note)
            self._evidence.append({
                "run": rid,
                "assessed": status != "not-assessed",
                "state": status,
                "harness": None if harness is None else ("pass" if harness else "fail"),
                "disagreement": note or None,
                "detail": detail,
            })
            rows.append((rid, status, detail, note))
        if not rows:
            return R("n/a", "no run with a task spec and a state snapshot")
        bad = [row for row in rows if row[1] == "fail"]
        if bad:
            parts = []
            for rid, _status, detail, note in bad:
                bit = f"{rid}: {detail}"
                if note:
                    bit += f"; {note}"
                parts.append(bit)
            return R("fail", "; ".join(parts))
        open_paths = [row for row in rows if row[1] == "not-assessed"]
        if open_paths:
            return R("not-assessed", "; ".join(f"{rid}: {detail}" for rid, _status, detail, _note in open_paths))
        ids = ", ".join(rid for rid, *_ in rows)
        text = f"task-spec postconditions hold over {len(rows)} run(s): {ids}"
        notes = [f"{rid}: {note}" for rid, _status, _detail, note in rows if note]
        if notes:
            text += "; " + "; ".join(notes)
        return R("pass", text)
