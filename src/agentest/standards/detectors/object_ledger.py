"""Per-object effect ledger for duplicate side effects (T1-006, T1-011, T2-003).

Within one run, the existing rule still decides. This module adds the comparison
the within-run counter never makes: the same effect on the same object in a later
turn or another run of the same conversation.

An effect is a ledger entry (``agentest.state_change``) or a state-diff path, not
a tool call. Object identity comes from id-like fields on the call's arguments and
result, and from declared governance objects (task-spec ``in_scope`` segments, the
ledger ``object`` when it names one of those, approval object/target). Approvals,
idempotent tools (MCP ``idempotentHint``), retries whose earlier result is an
error, and records that change no state are not a second effect.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict

from agentest.standards import signals as SG
from agentest.standards.expr import ok

IDS = ("T1-006", "T1-011", "T2-003")

DESCRIPTION = (
    "Non-idempotent state-changing tools (MCP idempotentHint=false) run at most once per identical arguments in a run. "
    "Across every turn and run of one conversation, the same effect on the same object is counted from state diffs and "
    "ledger entries, not from calls. Object identity is an id-like field in the arguments or result, or a declared "
    "governance object. An approval, an idempotent repeat (idempotentHint=true), a retry after an error result, and a "
    "record that changes no state are not a second effect."
)

_ID_VALUE = re.compile(r"(?=.*\d)(?=.*[A-Za-z])[\w.-]{3,}")  # rx: format
_ID_KEY = re.compile(r"(?i)(?:^id$|_id$|^object$|^reference$|^ref$)")  # rx: format
_FREE_KEYS = {"reason", "note", "notes", "description", "message", "comment", "comments", "status", "decision",
              "text", "summary", "content", "policy", "policy_version", "approver", "error", "outcome"}
_IDEM_PARTS = {"idempotency", "nonce", "uuid", "attempt", "client", "dedup", "dedupe", "correlation"}
_NOOP_TRUE = {"duplicate", "deduplicated", "deduped", "already_exists", "already_done", "already_recorded",
              "already_applied", "already_processed", "replayed", "idempotent_replay", "no_op", "unchanged"}
_NOOP_FALSE = {"changed", "created", "applied", "updated", "written", "executed", "modified"}
_BEFORE_AFTER = (("before", "after"), ("previous", "current"), ("old", "new"), ("prev_state", "new_state"),
                 ("previous_status", "status"), ("old_status", "new_status"))


def _parts(name: str) -> set[str]:
    return {w for w in re.split(r"[\W_]+", str(name).lower()) if w}


def _json_obj(s):
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s or "")
    except (ValueError, TypeError):
        return None


def _id_values(obj) -> set[str]:
    """Identifier values of id-like fields. Free text and idempotency keys are not object identity."""
    out: set[str] = set()

    def walk(x, key: str = "") -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, str(k))
            return
        if isinstance(x, list):
            for v in x:
                walk(v, key)
            return
        if not key or key.lower() in _FREE_KEYS or (_parts(key) & _IDEM_PARTS):
            return
        if _ID_KEY.search(key):
            s = str(x)
            if _ID_VALUE.fullmatch(s):
                out.add(s)

    walk(obj)
    return out


def _declared_ids(c, r) -> set[str]:
    """Objects the trace or the governance metadata names, not ids the agent minted in a result."""
    ids: set[str] = set()
    spec = SG.task_spec(r) or {}
    for path in spec.get("in_scope") or []:
        for seg in str(path).split("."):
            if _ID_VALUE.fullmatch(seg):
                ids.add(seg)
    published = c.a.g("objects", default=None)
    if isinstance(published, (list, tuple)):
        ids |= {str(x) for x in published if _ID_VALUE.fullmatch(str(x))}
    for ap in r.approvals or []:
        attrs = ap.get("attrs") or {}
        for key in ("target", "object"):
            raw = attrs.get(f"agentest.approval.{key}") or ap.get(key) or ""
            if _ID_VALUE.fullmatch(str(raw)):
                ids.add(str(raw))
    return ids


def _noop(t) -> bool:
    v = _json_obj(t.result)
    if not isinstance(v, dict):
        return False
    low = {str(k).lower(): x for k, x in v.items()}
    if any(low.get(k) is True for k in _NOOP_TRUE) or any(low.get(k) is False for k in _NOOP_FALSE):
        return True
    return any(a in low and b in low and low[a] is not None and json.dumps(low[a], sort_keys=True, default=str) == json.dumps(low[b], sort_keys=True, default=str)
               for a, b in _BEFORE_AFTER)


def _approval(t) -> bool:
    """A sign-off record: approved/granted is a boolean and the call does not mint a new record id."""
    v = _json_obj(t.result)
    if not isinstance(v, dict):
        return False
    low = {str(k).lower(): x for k, x in v.items()}
    if not any(isinstance(low.get(k), bool) for k in ("approved", "granted")):
        return False
    return not (_id_values(v) - _id_values(t.args))


def _helpers():
    from agentest.standards import rules as R

    return R


def _exempt(c, t) -> bool:
    R = _helpers()
    if t.error or c.a.ann(t.name, "idempotentHint") or not c.a.is_write(t.name):
        return True
    if _noop(t) or _approval(t) or R._result_refused(t):
        return True
    return False


def _object_ids(args, result, data: dict, gov: set[str]) -> set[str]:
    ids = _id_values(args)
    echoed = _id_values(result) & (ids | gov)
    ids |= echoed
    declared = str((data or {}).get("object") or "")
    if _ID_VALUE.fullmatch(declared) and (not ids or declared in ids or declared in gov):
        ids.add(declared)
    return ids


def _match(c, r, kind: str, cursor: dict[str, int]):
    """The next successful call of this tool, in order. None when every call of it failed."""
    named = [t for t in r.tools if t.name == kind]
    if named and all(t.error for t in named):
        return None
    ok = [t for t in c.ok_writes(r) if t.name == kind]
    n = cursor.get(kind, 0)
    cursor[kind] = n + 1
    if not ok:
        return None
    return ok[n] if n < len(ok) else ok[-1]


def _diff_objects(c, r, gov: set[str]) -> set[tuple[str, str]]:
    """State-diff paths that name an object a non-exempt write in this run touched."""
    init = SG.initial_state(r)
    if init is None or not isinstance(r.final_state, dict):
        return set()
    out: set[tuple[str, str]] = set()
    for path in SG.state_diff(init, r.final_state):
        segs = {seg for seg in path.split(".") if _ID_VALUE.fullmatch(seg)}
        if not segs:
            continue
        for t in c.ok_writes(r):
            if _exempt(c, t):
                continue
            ids = _id_values(t.args)
            shared = ids & segs
            if not shared and not ids and segs & gov:
                shared = segs & gov
            if not shared:
                continue
            for obj in shared:
                out.add((t.name, obj))
            break
    return out


def effects_of(c, r) -> set[tuple[str, str]]:
    """(effect kind, object id) pairs this run actually applied. Repeats inside the run collapse to one pair."""
    gov = _declared_ids(c, r)
    out: set[tuple[str, str]] = set()
    cursor: dict[str, int] = {}
    seen_eid: set[str] = set()
    for entry in r.executed():
        kind = str(entry.get("effect") or "")
        data = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        eid = str(data.get("effect_id") or "")
        if eid and eid in seen_eid:
            continue
        if kind and kind in c.a.tools and c.a.ann(kind, "idempotentHint"):
            continue
        if kind and kind in c.a.tools and not c.a.is_write(kind):
            continue
        call = _match(c, r, kind, cursor) if kind else None
        if call is None and kind and any(t.name == kind and t.error for t in r.tools):
            continue  # the attempt failed; a later successful retry is the first effect
        if call is not None and _exempt(c, call):
            continue
        args = call.args if call is not None else {}
        result = _json_obj(call.result) if call is not None else {}
        ids = _object_ids(args, result if isinstance(result, dict) else {}, data, gov)
        if eid:
            seen_eid.add(eid)
        for obj in ids:
            out.add((kind or "effect", obj))
    return out | _diff_objects(c, r, gov)


def cross_turn_findings(c, runs) -> list[str]:
    """Effects on one object in two or more turns/runs of the same conversation."""
    groups: dict[str, list] = defaultdict(list)
    for r in runs:
        if r.conversation:
            groups[r.conversation].append(r)
    bad: list[str] = []
    for cid, turns in groups.items():
        if len(turns) < 2:
            continue
        hit: dict[tuple[str, str], set[str]] = defaultdict(set)
        for r in turns:
            where = f"{r.input_id}#{r.rep}"
            for key in effects_of(c, r):
                hit[key].add(where)
        for (kind, obj), where in sorted(hit.items()):
            if len(where) > 1:
                bad.append(f"{cid}: {kind}({obj}) x{len(where)} turns {sorted(where)[:4]}")
    return bad


def _scope(c, tid: str):
    if tid == "T1-006":
        replay = c.fam("replay")
        if replay:
            return replay
    return c.runs


def combine(c, tid: str, previous):
    """Keep a within-run fail as it was. A cross-turn duplicate fails a pass (or an n/a that now has a signal)."""
    base = previous(c)
    if base.status == "fail":
        return base
    found = cross_turn_findings(c, _scope(c, tid))
    if not found:
        return base
    return ok(False, f"repeated side effects across turns: {found[:5]}")


def install(rules: dict) -> None:
    """Wrap T1-006, T1-011 and T2-003. Idempotent, so a second import does not stack."""
    for tid in IDS:
        if tid not in rules:
            continue
        what, fn = rules[tid]
        if getattr(fn, "_object_ledger", False):
            rules[tid] = (DESCRIPTION, fn)
            continue

        def wrapped(c, _fn=fn, _tid=tid):
            return combine(c, _tid, _fn)

        wrapped._object_ledger = True  # type: ignore[attr-defined]
        rules[tid] = (DESCRIPTION, wrapped)
