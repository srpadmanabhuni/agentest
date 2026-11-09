"""T1-001 state-outcome detector.

Every run that publishes a task spec is judged here. Postconditions are recomputed
from ``agentest.initial_state``, ``agentest.final_state`` and the spec. An
``effects.<object>.new_<collection>`` or ``effects.<object>.sum_<collection>.<field>``
path is the snapshot difference for whatever collection and field the path names.
The harness attribute ``agentest.postcondition.result`` is compared afterwards and
any disagreement is recorded; it never decides the verdict.

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


def _as_map(bucket) -> dict:
    """A collection as a map of record id to record. A list uses each record's ``id`` when it has one."""
    if isinstance(bucket, dict):
        return {str(k): v for k, v in bucket.items() if isinstance(v, dict)}
    if isinstance(bucket, list):
        out = {}
        for i, rec in enumerate(bucket):
            if not isinstance(rec, dict):
                continue
            key = str(rec["id"]) if isinstance(rec.get("id"), str) and rec["id"] else str(i)
            out[key] = rec
        return out
    return {}


def _locate(state, name: str) -> dict | None:
    """The collection named by the spec path, at the snapshot root or one level down. None when it is absent."""
    if not isinstance(state, dict) or not name:
        return None
    if name in state and isinstance(state.get(name), (dict, list)):
        return _as_map(state[name])
    found = [child[name] for child in state.values()
             if isinstance(child, dict) and name in child and isinstance(child.get(name), (dict, list))]
    if len(found) == 1:
        return _as_map(found[0])
    return None


def _object_ids(key: str, rec: dict) -> list[str]:
    """Subject ids named by the record (any ``id`` / ``*_id`` field). The record key is the fallback."""
    ids: list[str] = []
    for fk, fv in rec.items():
        if isinstance(fv, str) and fv and (fk == "id" or fk.endswith("_id")) and fv not in ids:
            ids.append(fv)
    if not ids and key:
        ids.append(key)
    return ids


def _effect_aliases(spec: dict) -> dict[str, str]:
    """Metric renames declared on the task spec. The checker supplies none of its own."""
    raw = spec.get("effect_aliases") if isinstance(spec, dict) else None
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if isinstance(k, str) and isinstance(v, str) and k and v}


def _expand_alias(path: str, aliases: dict[str, str], predicate_alias: str | None) -> str:
    """Rewrite ``effects.<object>.<name>`` when the spec maps ``<name>`` to a ``new_`` or ``sum_`` metric."""
    if not path.startswith("effects."):
        return path
    obj, sep, metric = path[len("effects."):].rpartition(".")
    if not sep or not obj or not metric:
        return path
    if metric.startswith("new_") or metric.startswith("sum_"):
        return path
    target = predicate_alias or aliases.get(metric)
    if not target:
        return path
    return f"effects.{obj}.{target}"


def _parse_effect(path: str) -> tuple[str, str, str, str | None] | None:
    """``new_<collection>`` or ``sum_<collection>.<field>`` taken from the path. None when it is not that shape."""
    if not path.startswith("effects."):
        return None
    parts = path[len("effects."):].split(".")
    if len(parts) >= 2 and parts[-1].startswith("new_") and len(parts[-1]) > len("new_"):
        return "count", ".".join(parts[:-1]), parts[-1][len("new_"):], None
    if len(parts) >= 3 and parts[-2].startswith("sum_") and len(parts[-2]) > len("sum_") and parts[-1]:
        return "sum", ".".join(parts[:-2]), parts[-2][len("sum_"):], parts[-1]
    return None


def _records_for(rows: list[tuple[str, dict]], obj: str) -> list[dict]:
    return [rec for key, rec in rows if obj in _object_ids(key, rec)]


def _uniform_sum(records: list[dict], field: str):
    """Sum ``field`` when every new record has it and every value is the same numeric type. None otherwise."""
    if not records:
        return None
    values = []
    for rec in records:
        if field not in rec:
            return None
        values.append(rec[field])
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in values):
        return None
    if len({type(v) for v in values}) != 1:
        return None
    return sum(values)


def _effect_value(path: str, initial, final):
    """The snapshot-difference metric named by ``path``, or None when it cannot be resolved.

    ``new_<collection>`` is 0 when that collection is in both snapshots and the object gained
    no records, including when the collection is empty. A collection missing from either
    snapshot is unresolved. A sum over no new records, a missing field, a non-numeric value,
    or mixed numeric types is unresolved, and is not turned into 0.
    """
    parsed = _parse_effect(path)
    if parsed is None or not isinstance(initial, dict) or not isinstance(final, dict):
        return None
    kind, obj, collection, field = parsed
    before = _locate(initial, collection)
    after = _locate(final, collection)
    if before is None or after is None:
        return None
    new_for = _records_for([(k, rec) for k, rec in after.items() if k not in before], obj)
    if kind == "count":
        return len(new_for)
    return _uniform_sum(new_for, field or "")


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


def _resolve(path: str, final_state, initial, aliases: dict[str, str], predicate_alias: str | None) -> tuple[bool, object, object]:
    """``(resolved, value, initial value for a stored path)``."""
    expanded = _expand_alias(path, aliases, predicate_alias)
    if expanded.startswith("effects."):
        got = _effect_value(expanded, initial, final_state)
        return (got is not None), got, None
    ok_final, got = _path_in(final_state, path)
    if not ok_final:
        return False, None, None
    before = _path_in(initial, path)[1] if isinstance(initial, dict) else None
    return True, got, before


def recompute(spec: dict, final_state, initial_state) -> tuple[str, str]:
    """Evaluate spec postconditions against the recorded snapshots.

    Returns ``(pass|fail|not-assessed|n/a, detail)``. ``effects.<object>.new_<collection>`` is the
    count of records added to that collection for the object. ``effects.<object>.sum_<collection>.<field>``
    is the sum of that field over those records. Names come from the path, or from ``effect_aliases``
    on the spec. A path that cannot be resolved is not assessed, and is not a failure.
    """
    if not isinstance(final_state, dict):
        return "n/a", "no final_state snapshot"
    spec = spec if isinstance(spec, dict) else {}
    pcs = [p for p in (spec.get("postconditions") or []) if isinstance(p, dict) and p.get("path")]
    initial = initial_state if isinstance(initial_state, dict) else None
    aliases = _effect_aliases(spec)
    bad: list[str] = []
    unresolved: list[str] = []
    for cr in pcs:
        op = str(cr.get("op") or "eq")
        path = str(cr["path"])
        want = cr.get("value")
        one = cr.get("alias") if isinstance(cr.get("alias"), str) else None
        resolved, got, before = _resolve(path, final_state, initial, aliases, one)
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
        if before is not None:
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
            status, detail = recompute(SG.task_spec(r) or {}, r.final_state, SG.initial_state(r))
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
