"""Shared helpers for the extension-pack rules. Everything reads :class:`agentest.standards.otel.Run` (built from OTLP spans)
and the agent's published metadata, exactly like the 130 core rules; nothing here knows an agent or a framework."""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from agentest.standards import packs as _registry
from agentest.standards.expr import R, ok  # noqa: F401  (re-exported for the pack modules)
from agentest.standards.otel import Run, _text_of
from agentest.standards.rules import NA, Ctx, need  # noqa: F401


def pack_rule(*ids: str) -> Callable:
    """Register a rule under pack IDs; the ``what`` text is the catalogue row's ``rule`` field (single source of truth)."""
    rows = _registry.rows()
    if not rows:  # the pack catalogue is not installed (a trimmed wheel): the packs are simply absent, importing agentest must still work
        return lambda fn: fn
    missing = [i for i in ids if i not in rows]
    if missing:  # not an assert: the guard must survive python -O
        raise KeyError(f"{', '.join(missing)} has no row in catalog/packs")

    def deco(fn):
        for i in ids:
            _registry.PACK_RULES[i] = (rows[i]["rule"], _bind(fn, i))
        return fn

    return deco


def _bind(fn: Callable, tid: str) -> Callable:
    """The rule function with its check ID fixed (one function may serve several IDs). A published fact or attribute of the
    wrong shape (a list where an object is expected, text where a number is) makes the check n/a, not a crash of the whole run."""

    def run(c: Ctx) -> R:
        try:
            return fn(c, tid)
        except NA:
            raise
        except (AttributeError, TypeError, ValueError, KeyError, IndexError, RecursionError) as e:
            raise NA(f"an input is not in the expected shape ({type(e).__name__}: {str(e)[:80]})") from e

    return run


def as_set(v: object) -> set[str]:
    """A governance list as a set of names; a lone string is one name, anything else is empty."""
    if isinstance(v, str):
        return {v} if v else set()
    return {str(x) for x in v} if isinstance(v, (list, tuple, set, frozenset)) else set()


def as_dict(v: object) -> dict:
    return v if isinstance(v, dict) else {}


def as_int(v: object, default: int) -> int:
    try:
        return int(v)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return default


NUM_TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?")  # a number as written in text (thousands separators allowed)
AMOUNT_KEY = re.compile(r"amount|total|price|cost|fee|sum|qty|quantity|limit", re.I)  # argument names that carry an amount


def norm_text(s: object) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def dumps(x: object) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, default=str)


# ---------------------------------------------------------------- span views (multi-agent)

def _cache(r: Run) -> dict:
    return r.__dict__.setdefault("_pack_cache", {})  # span indexes, built once per run (a long trace would otherwise cost O(n) per lookup)


def by_id(r: Run) -> dict[str, dict]:
    c = _cache(r)
    if "ix" not in c:
        c["ix"] = {s["id"]: s for s in r.spans}
    return c["ix"]


def agent_spans(r: Run) -> list[dict]:
    return [s for s in r.spans if s["op"] == "invoke_agent" and s["agent"]]


def tool_spans(r: Run) -> list[dict]:
    return [s for s in r.spans if s["op"] == "execute_tool"]


def ancestors(r: Run, s: dict) -> list[dict]:
    """Enclosing spans, nearest first."""
    ix, cur = by_id(r), s
    out: list[dict] = []
    while cur["pack_parent"] and cur["pack_parent"] in ix and len(out) < 64:
        cur = ix[cur["pack_parent"]]
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
    c = _cache(r)
    if "kids" not in c:
        kids: dict[str, list[str]] = {}
        for s in r.spans:
            kids.setdefault(s["pack_parent"], []).append(s["id"])
        c["kids"] = kids
    out: set[str] = set()
    todo = [span_id]
    while todo:
        for k in c["kids"].get(todo.pop(), []):
            if k not in out:
                out.add(k)
                todo.append(k)
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
    return as_dict(c.a.g("multiAgent", default={}))


def priv_spec(c: Ctx) -> dict:
    return as_dict(c.a.g("privacy", default={}))


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
    return [s for s in tool_spans(r) if c.a.is_write(span_tool(s)) and not s["pack_error"]]


def escalation_tools(c: Ctx) -> set[str]:
    esc = as_dict(c.a.g("escalation", default={}))
    return as_set(ma_spec(c).get("escalationTools")) | ({str(esc["handoffTool"])} if esc.get("handoffTool") else set())


def privacy_levels(c: Ctx) -> dict[str, str]:
    return {str(k): str(v) for k, v in as_dict(priv_spec(c).get("classLevels")).items()}
