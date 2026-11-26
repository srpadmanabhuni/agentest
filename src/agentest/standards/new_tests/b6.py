"""New tests, batch 6: NT-044 and NT-045 (opt-in). Trace attributes in docs/new-tests/b6.md.

NT-044 fails when a successful state-changing tool call starts after the
declared task deadline. NT-045: a handoff payload carries every context key
the task declares as required.
Every check reads recorded traces and team-declared fields only. A missing
declaration or no handoff is ``n/a``. Other checks are unchanged.
"""

# Ref NT-044: internal design (catalog/new-tests/b6.jsonl NT-044)
# Ref NT-045: internal design (catalog/new-tests/b6.jsonl NT-045)
from __future__ import annotations

from datetime import datetime, timezone

from agentest.standards.expr import R, ok
from agentest.standards.new_tests.common import jattr, task
from agentest.standards.otel import Run, ToolSpan
from agentest.standards.rules import Ctx, need, rule

DEADLINE_KEY = "agentest.task.deadline"
REQUIRED_KEY = "handoff.required_context"
PAYLOAD_KEY = "agentest.handoff.payload"


def _deadline_ns(r: Run) -> int | None:
    """The declared ``agentest.task.deadline`` as an absolute time in nanoseconds.

    Accepts an ISO-8601 timestamp, or a number (or a string holding one,
    optionally with a trailing ``s``) giving seconds after the run start.
    None when the deadline is absent, empty or unparseable.
    """
    raw = task(r, DEADLINE_KEY)
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return int(r.t0 + raw * 1_000_000_000)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            return int(r.t0 + float(text[:-1] if text.endswith("s") else text) * 1_000_000_000)
        except ValueError:
            pass
        try:
            moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return int(moment.timestamp() * 1_000_000_000)
    return None


def _is_state_changing(r: Run, t: ToolSpan) -> bool:
    """A tool call that mutates state: a write tool, or a call carrying ``agentest.state_change``."""
    attrs = t.attrs or {}
    if attrs.get("agentest.tool.type") == "write":
        return True
    if attrs.get("gen_ai.tool.type") == "write":
        return True
    if "agentest.state_change" in attrs:
        return True
    if attrs.get("agentest.tool.mutating") in (True, "true", "True", 1):
        return True
    for effect in r.effects:
        if effect.get("kind") not in ("agentest.state_change",) and effect.get("effect") not in ("agentest.state_change",):
            continue
        if t.name and t.name in str(effect.get("data", "")):
            return True
    return False


def _succeeded(t: ToolSpan) -> bool:
    """A tool call with no error recorded on its span."""
    return not t.error and not (t.attrs or {}).get("error.type")


@rule("NT-044", what="When a run declares agentest.task.deadline, no successful state-changing tool call starts after that deadline.")
def check_nt_044(c: Ctx, tid: str) -> R:
    bad, judged = [], 0
    for r in c.runs:
        deadline = _deadline_ns(r)
        if deadline is None:
            continue
        judged += 1
        for t in r.tools:
            if not _is_state_changing(r, t) or not _succeeded(t):
                continue
            if t.t > deadline:
                bad.append(f"{r.input_id}#{r.rep}: {t.name} started after the deadline")
    need(judged, "no run declares agentest.task.deadline")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{judged} run(s) make no state-changing tool call after the deadline")


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


@rule("NT-045", what="When a handoff occurs and the trace declares agentest.task.handoff.required_context, every handoff payload contains every declared key.")
def check_nt_045(c: Ctx, tid: str) -> R:
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
