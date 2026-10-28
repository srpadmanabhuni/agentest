"""Multi-span trace checks (v3.5): loop, thrash, recursion and state drift.

Generic rules over the standard trace view (:class:`agentest.standards.otel.Run`): tool spans in start order, the
span tree (``spanId`` / ``parentSpanId``), handoffs, MCP tool annotations and ``agentest.final_state``. No agent,
tool or domain name appears here. Thresholds are ``BUDGET`` keys, overridable in the config ``thresholds``:

* ``loop_cycles`` (3): a block of >= 2 tool calls repeated this many times in a row, with identical arguments.
* ``recursion_depth`` (3): the same agent (or tool) nested in itself this deep, or entered this often by handoff.
"""

from __future__ import annotations

import json

from agentest.standards.expr import R, ok
from agentest.standards.otel import Run, ToolSpan
from agentest.standards.rules import BUDGET, Ctx, _dumps, need, rule

BUDGET.setdefault("loop_cycles", 3)
BUDGET.setdefault("recursion_depth", 3)
MAX_CYCLE = 6  # longest repeated block searched for (X-004 covers blocks of one call)


# ------------------------------------------------------------------ X-021 loop

def loops(r: Run, cycles: int) -> list[str]:
    """Blocks of 2..MAX_CYCLE calls (>= 2 distinct tools) repeated ``cycles`` times back to back, same arguments."""
    sig = [(t.name, _dumps(t.args)) for t in r.tools]
    found = []
    for k in range(2, MAX_CYCLE + 1):
        i = 0
        while i + k * cycles <= len(sig):
            block = sig[i:i + k]
            if len({n for n, _ in block}) > 1 and all(sig[i + j * k:i + (j + 1) * k] == block for j in range(1, cycles)):
                found.append("→".join(n for n, _ in block))
                i += k * cycles
            else:
                i += 1
    return found


@rule("X-021", what="No multi-span loop: a block of 2+ tool calls with identical arguments is not repeated 3 times in a row (no progress).")
def _x_021(c: Ctx, tid: str) -> R:
    cycles = int(BUDGET["loop_cycles"])
    need(any(len(r.tools) >= 2 * cycles for r in c.runs), f"no run with {2 * cycles}+ tool calls")
    bad = [f"{r.input_id}:{b}" for r in c.runs for b in loops(r, cycles)]
    return ok(not bad, f"loop without progress: {sorted(set(bad))[:4]}" if bad else "no repeated multi-call loop")


# ------------------------------------------------------------------ X-022 thrash

def _scalars(args: dict) -> dict:
    return {k: v for k, v in args.items() if isinstance(v, (str, int, float, bool)) or v is None}


def thrash(c: Ctx, r: Run) -> list[str]:
    """Do / change / change-back on one object: three successive successful calls of one write tool where the third
    restores the first's arguments exactly, the middle one shares an argument value with them (the same object) and
    differs in others; or, with governance ``compensations``, X(a) → undo → X(a) again."""
    ws = c.ok_writes(r)
    out = []
    by_tool: dict[str, list[ToolSpan]] = {}
    for t in ws:
        by_tool.setdefault(t.name, []).append(t)
    for name, ts in by_tool.items():
        for a, b, d in zip(ts, ts[1:], ts[2:], strict=False):
            sa, sb = _scalars(a.args), _scalars(b.args)
            same = {k for k in sa if k in sb and sa[k] == sb[k]}
            if _dumps(a.args) == _dumps(d.args) != _dumps(b.args) and same and set(sa) == set(sb):
                out.append(f"{name}:{sorted(set(sa) - same)}")
    comp = {str(k): str(v) for k, v in (c.a.g("compensations", default={}) or {}).items()}
    for i, t in enumerate(ws):
        undo = comp.get(t.name)
        if not undo:
            continue
        rest = ws[i + 1:]
        j = next((n for n, u in enumerate(rest) if u.name == undo), None)
        if j is not None and any(v.name == t.name and _dumps(v.args) == _dumps(t.args) for v in rest[j + 1:]):
            out.append(f"{t.name}→{undo}→{t.name}")
    return out


@rule("X-022", what="No thrash: an object is not set, changed and set back (or done, undone and redone) by successive writes in one run.")
def _x_022(c: Ctx, tid: str) -> R:
    need(any(len(c.ok_writes(r)) >= 3 for r in c.runs), "no run with 3+ successful writes")
    bad = [f"{r.input_id}:{x}" for r in c.runs for x in thrash(c, r)]
    return ok(not bad, f"write thrash: {sorted(set(bad))[:4]}" if bad else "no write thrash")


# ------------------------------------------------------------------ X-023 recursion

def _key(s: dict) -> tuple[str, str] | None:
    if s["op"] == "invoke_agent" and s["agent"]:
        return ("agent", s["agent"])
    if s["op"] == "execute_tool" and (s.get("tool") or s["name"]):
        return ("tool", s.get("tool") or s["name"])
    return None


def nesting(r: Run) -> dict[tuple[str, str], int]:
    """Deepest self-nesting per agent / tool: how many spans with that key lie on one root path."""
    by_id = {s.get("id"): s for s in r.spans if s.get("id")}
    depth: dict[tuple[str, str], int] = {}
    for s in r.spans:
        k = _key(s)
        if k is None:
            continue
        n, cur, seen = 1, s, set()
        while cur.get("parent") in by_id and cur["parent"] not in seen:
            seen.add(cur["parent"])
            cur = by_id[cur["parent"]]
            n += _key(cur) == k
        depth[k] = max(depth.get(k, 0), n)
    return depth


def nested_any(r: Run) -> bool:
    """Some agent/tool span has an agent/tool span among its ancestors."""
    by_id = {s.get("id"): s for s in r.spans if s.get("id")}
    return any(_key(s) and any(_key(x) for x in _ancestors(by_id, s)) for s in r.spans)


def _ancestors(by_id: dict, s: dict) -> list[dict]:
    out, seen = [], set()
    while s.get("parent") in by_id and s["parent"] not in seen:
        seen.add(s["parent"])
        s = by_id[s["parent"]]
        out.append(s)
    return out


@rule("X-023", what="No runaway recursion: no agent or tool is nested in itself 3 deep, and no agent is re-entered by handoff 3 times in one run.")
def _x_023(c: Ctx, tid: str) -> R:
    lim = int(BUDGET["recursion_depth"])
    need(any(r.handoffs or nested_any(r) for r in c.runs), "no handoffs and no nested agent/tool spans recorded")
    bad = []
    for r in c.runs:
        bad += [f"{r.input_id}:{k[0]} {k[1]} nested {n}x" for k, n in nesting(r).items() if n >= lim]
        entered: dict[str, int] = {}
        for _src, dst, _t in r.handoffs:
            entered[dst] = entered.get(dst, 0) + 1
        bad += [f"{r.input_id}:handoff to {a} {n}x" for a, n in entered.items() if a and n >= lim]
    return ok(not bad, f"recursion: {sorted(set(bad))[:4]}" if bad else "no runaway recursion")


# ------------------------------------------------------------------ X-024 state drift

def _is_id(k: str) -> bool:
    return k == "id" or k.endswith(("_id", "Id", "ID"))


def _same(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or str(a).lower() == str(b).lower()
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)


def _records(x, ids: dict) -> list[dict]:
    """Dicts inside a JSON value that carry one of the identity pairs."""
    out = []
    if isinstance(x, dict):
        if any(k in x and _same(x[k], v) for k, v in ids.items()):
            out.append(x)
        for v in x.values():
            out += _records(v, ids)
    elif isinstance(x, list):
        for v in x:
            out += _records(v, ids)
    return out


def _json(s: str):
    try:
        return json.loads(s)
    except (TypeError, ValueError):
        return None


def drift(c: Ctx, r: Run) -> list[str]:
    """A successful idempotent write (MCP ``idempotentHint``: it sets a target state) of ``field=value`` on an object
    (``*_id`` argument) whose object later reads, or ends in ``agentest.final_state``, with another value for that
    field while no later write touched the object."""
    host = bool(c.a.g("approval", "hostGated", default=False))
    gated = c.gated() if host else set()
    ws = [t for t in c.ok_writes(r) if c.a.ann(t.name, "idempotentHint") and t.name not in gated]
    out = []
    for w in ws:
        sc = _scalars(w.args)
        ids = {k: v for k, v in sc.items() if _is_id(k) and v not in (None, "")}
        fields = {k: v for k, v in sc.items() if not _is_id(k)}
        if not ids or not fields:
            continue
        later = [t for t in r.tools if t.t > w.t and not t.error]
        touched = [t for t in later if c.a.is_write(t.name) and any(_same(t.args.get(k), v) for k, v in ids.items())]
        stop = min((t.t for t in touched), default=None)
        reads = [t for t in later if not c.a.is_write(t.name) and (stop is None or t.t < stop)
                 and any(_same(t.args.get(k), v) for k, v in ids.items())]
        views = [(f"read {t.name}", rec) for t in reads for rec in _records(_json(t.result), ids)]
        if stop is None and r.final_state:
            views += [("final_state", rec) for rec in _records(r.final_state, ids)]
        for where, rec in views:
            diff = [f for f, v in fields.items() if f in rec and isinstance(rec[f], (str, int, float, bool)) and not _same(rec[f], v)]
            if diff:
                out.append(f"{w.name} set {diff[0]}={fields[diff[0]]!r}, {where} shows {rec[diff[0]]!r}")
                break
    return out


@rule("X-024", what="No state drift: after an idempotent (set-state) write, later reads and the final state of that object show the written values.")
def _x_024(c: Ctx, tid: str) -> R:
    need(any(c.a.ann(t.name, "idempotentHint") and _scalars(t.args) and any(_is_id(k) for k in t.args)
             for r in c.runs for t in c.ok_writes(r)), "no successful idempotent write (MCP idempotentHint) on an object id recorded")
    bad = [f"{r.input_id}:{x}" for r in c.runs for x in drift(c, r)]
    return ok(not bad, f"state drift: {bad[:3]}" if bad else "written state held")
