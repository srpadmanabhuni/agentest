"""New tests, batch 6: NT-044, NT-045 (opt-in). Trace attributes in docs/new-tests/b6.md.

NT-044: No state-changing tool calls succeed after a declared task deadline.
NT-045: A handoff payload carries every context key the task declares as required.
Every check reads recorded traces and team-declared fields only. A missing declaration or no handoff is ``n/a``.
Other checks are unchanged.
"""
# Ref NT-044: internal design (catalog/new-tests/b6.jsonl NT-044, closes A002)
# Ref NT-045: internal design (catalog/new-tests/b6.jsonl NT-045)

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from agentest.standards.expr import R, ok
from agentest.standards.new_tests.common import jattr, task
from agentest.standards.otel import Run
from agentest.standards.rules import Ctx, need, rule

REQUIRED_KEY = "handoff.required_context"
PAYLOAD_KEY = "agentest.handoff.payload"


def _deadline_ns(raw: Any, t0: int) -> int | None:
    """Parse a task deadline into epoch nanoseconds, or None when unreadable / non-finite.

    Accepts:
    - relative seconds (int or float): added to root start t0
    - epoch nanoseconds (int >= 1_000_000_000_000_000_000)
    - ISO-8601 string (with offset, or naive treated as UTC)
    """
    if raw in (None, ""):
        return None
    if isinstance(raw, (int, float)):
        if isinstance(raw, float) and (math.isnan(raw) or math.isinf(raw)):
            return None
        if raw >= 1_000_000_000_000_000_000:
            return int(raw)
        if raw >= 0:
            return t0 + int(raw * 1_000_000_000)
        return None
    if isinstance(raw, str):
        val = raw.strip()
        try:
            num = float(val)
            if math.isnan(num) or math.isinf(num):
                return None
            if num >= 1_000_000_000_000_000_000:
                return int(num)
            if num >= 0:
                return t0 + int(num * 1_000_000_000)
            return None
        except ValueError:
            pass
        try:
            dt_str = val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(dt_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return int(dt.timestamp() * 1_000_000_000)
        except (ValueError, OverflowError):
            return None
    return None


@rule("NT-044", what="No state-changing tool call succeeds after a declared agentest.task.deadline.")
def _nt_044(c: Ctx, tid: str) -> R:
    bad, judged = [], 0
    for r in c.runs:
        raw = task(r, "deadline")
        if raw in (None, ""):
            continue
        start = r.t0 or min((s["t0"] for s in r.spans), default=0)
        dl = _deadline_ns(raw, start)
        need(dl is not None, f"unreadable deadline {raw!r}")
        judged += 1
        late = [t.name for t in c.ok_writes(r) if t.t > dl]
        if late:
            bad.append(f"{r.input_id}#{r.rep}: {len(late)} write(s) after deadline ({', '.join(late[:3])})")
    need(judged, "no agentest.task.deadline declared in trace")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{judged} run(s) with no state-changing calls after deadline")


def _is_handoff(s: dict) -> bool:
    """An agent invocation that received a handoff (``agentest.handoff.source``), or an explicit handoff span."""
    return s["name"] == "agentest.handoff" or bool(s["attrs"].get("agentest.handoff.source"))


def _required(r: Run) -> list[str] | None:
    """The declared ``agentest.task.handoff.required_context`` keys (a JSON list or a comma-separated string). None when absent."""
    raw = task(r, REQUIRED_KEY)
    if isinstance(raw, str):
        items = raw.split(",")
    elif isinstance(raw, list):
        items = [str(k) for k in raw]
    else:
        return None
    keys = [k.strip() for k in items if k.strip()]
    return keys or None


def _payload(s: dict) -> dict | None:
    """The handoff payload as a JSON object; None when it is absent or not an object."""
    p = jattr(s["attrs"], PAYLOAD_KEY)
    return p if isinstance(p, dict) else None


@rule("NT-045", what="When a handoff occurs and the trace declares agentest.task.handoff.required_context, the handoff payload includes every listed key.")
def _nt_045(c: Ctx, tid: str) -> R:
    bad, judged = [], 0
    for r in c.runs:
        keys = _required(r)
        if keys is None:
            continue
        handoffs = [s for s in r.spans if _is_handoff(s)]
        if not handoffs:
            continue
        judged += 1
        for s in handoffs:
            payload = _payload(s)
            missing = [k for k in keys if payload is None or k not in payload]
            if missing:
                who = s["attrs"].get("gen_ai.agent.name") or s["name"]
                bad.append(f"{r.input_id}#{r.rep}: handoff to {who} lacks {missing[:3]}")
    need(judged, "no handoff in a trace that declares agentest.task.handoff.required_context")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{judged} run(s) with a handoff carry every required key")
