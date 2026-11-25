"""New tests, batch 6: NT-045 (opt-in). Trace attributes in docs/new-tests/b6.md.

A handoff payload carries every context key the task declares as required.
Every check reads recorded traces and team-declared fields only. A missing declaration or no handoff is ``n/a``.
Other checks are unchanged.
"""
# Ref NT-045: internal design (catalog/new-tests/b6.jsonl NT-045)

from __future__ import annotations

from agentest.standards.expr import R, ok
from agentest.standards.new_tests.common import jattr, task
from agentest.standards.otel import Run
from agentest.standards.rules import Ctx, need, rule

REQUIRED_KEY = "handoff.required_context"
PAYLOAD_KEY = "agentest.handoff.payload"


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
