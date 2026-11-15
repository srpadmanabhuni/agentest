"""Shared helpers for the extension-pack rules. Everything reads :class:`agentest.standards.otel.Run` (built from OTLP spans)
and the agent's published metadata, exactly like the 130 core rules; nothing here knows an agent or a framework."""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from agentest.standards import packs as P
from agentest.standards.expr import R, ok  # noqa: F401  (re-exported for the pack modules)
from agentest.standards.otel import Run, _text_of
from agentest.standards.rules import NA, Ctx, need  # noqa: F401


def pack_rule(*ids: str) -> Callable:
    """Register a rule under pack IDs; the ``what`` text is the catalogue row's ``rule`` field (single source of truth)."""
    rows = P.rows()
    for i in ids:
        assert i in rows, f"{i} has no row in catalog/packs"

    def deco(fn):
        for i in ids:
            P.PACK_RULES[i] = (rows[i]["rule"], (lambda f, tid: lambda c: f(c, tid))(fn, i))
        return fn

    return deco


def norm_text(s: object) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def dumps(x: object) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, default=str)


# ---------------------------------------------------------------- span views (multi-agent)

def by_id(r: Run) -> dict[str, dict]:
    return {s["id"]: s for s in r.spans}


def agent_spans(r: Run) -> list[dict]:
    return [s for s in r.spans if s["op"] == "invoke_agent" and s["agent"]]


def tool_spans(r: Run) -> list[dict]:
    return [s for s in r.spans if s["op"] == "execute_tool"]


def ancestors(r: Run, s: dict) -> list[dict]:
    """Enclosing spans, nearest first."""
    ix, out, cur = by_id(r), [], s
    while cur["parent"] and cur["parent"] in ix and len(out) < 64:
        cur = ix[cur["parent"]]
        out.append(cur)
    return out


def enclosing_agent(r: Run, s: dict) -> str:
    """Name of the nearest enclosing ``invoke_agent`` span (not the span itself)."""
    return next((a["agent"] for a in ancestors(r, s) if a["op"] == "invoke_agent" and a["agent"]), "")


def agent_of(r: Run, s: dict) -> str:
    """The agent a span belongs to: its own gen_ai.agent.name, else the enclosing invoke_agent span's."""
    return s["agent"] or enclosing_agent(r, s)


def chain_of(r: Run, s: dict) -> list[str]:
    """Delegation chain of a span's agent, itself first, root last."""
    names = [agent_of(r, s)] if agent_of(r, s) else []
    names += [a["agent"] for a in ancestors(r, s) if a["op"] == "invoke_agent" and a["agent"] and a["agent"] != (names[0] if names else "")]
    return names


def descendants(r: Run, span_id: str) -> set[str]:
    out, todo = set(), [span_id]
    while todo:
        cur = todo.pop()
        for s in r.spans:
            if s["parent"] == cur and s["id"] not in out:
                out.add(s["id"])
                todo.append(s["id"])
    return out


def agent_names(r: Run) -> list[str]:
    seen: list[str] = []
    for s in r.spans:
        if s["op"] in ("invoke_agent", "execute_tool"):
            n = agent_of(r, s)
            if n and n not in seen:
                seen.append(n)
    return seen


def is_multi(r: Run) -> bool:
    return len(agent_names(r)) >= 2


def handoffs_of(r: Run) -> list[tuple[str, str, dict]]:
    """(delegator, delegate, span): an invoke_agent span that is not the root and has a delegator, from the explicit
    ``agentest.handoff.source`` attribute (an extension) or else from span nesting (standard)."""
    out = []
    for s in agent_spans(r):
        if s["root"]:
            continue
        src = str(s["attrs"].get("agentest.handoff.source") or "") or enclosing_agent(r, s)
        if src:
            out.append((src, s["agent"], s))
    return out


def multi_runs(c: Ctx) -> list[Run]:
    rs = [r for r in c.runs if is_multi(r)]
    need(rs, "fewer than two distinct agents appear in the trace (gen_ai.agent.name on invoke_agent / execute_tool spans)")
    return rs


def ma_spec(c: Ctx) -> dict:
    return c.a.g("multiAgent", default={}) or {}


def priv_spec(c: Ctx) -> dict:
    return c.a.g("privacy", default={}) or {}


def span_args(s: dict) -> dict:
    try:
        v = json.loads(s["attrs"].get("gen_ai.tool.call.arguments") or "{}")
    except ValueError:
        return {}
    return v if isinstance(v, dict) else {}


def span_result(s: dict) -> str:
    return str(s["attrs"].get("gen_ai.tool.call.result") or "")


def span_tool(s: dict) -> str:
    return str(s["attrs"].get("gen_ai.tool.name") or "")


def span_text_in(s: dict) -> str:
    return _text_of(s["attrs"].get("gen_ai.input.messages", ""))


def ok_writes(c: Ctx, r: Run) -> list[dict]:
    return [s for s in tool_spans(r) if c.a.is_write(span_tool(s)) and not s["error"]]


def escalation_tools(c: Ctx) -> set[str]:
    esc = c.a.g("escalation", default={}) or {}
    return set(ma_spec(c).get("escalationTools") or []) | ({str(esc["handoffTool"])} if esc.get("handoffTool") else set())


def tool_names_run(r: Run) -> set[str]:
    return {t.name for t in r.tools}


def privacy_levels(c: Ctx) -> dict[str, str]:
    return {str(k): str(v) for k, v in (priv_spec(c).get("classLevels") or {}).items()}
