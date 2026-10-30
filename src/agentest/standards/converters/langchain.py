"""LangChain / LangGraph converter (issue #1): messages or ``astream_events`` (v2) -> native record.

Accepted inputs, all read without importing LangChain:
  * message objects with ``.type`` / ``.content`` / ``.tool_calls`` / ``.tool_call_id`` (duck typed);
  * plain dicts ``{"type"|"role": ..., "content": ..., "tool_calls": [...]}``;
  * ``messages_to_dict`` output ``{"type": ..., "data": {...}}`` and ``dumpd`` output ``{"lc": 1, "kwargs": {...}}``;
  * ``astream_events(version="v2")`` event dicts (``on_chat_model_end``, ``on_tool_start``, ``on_tool_end``);
  * LangGraph state: a state dict ``{"messages": [...]}``, a ``StateSnapshot`` (``.values``), a checkpoint
    (``{"channel_values": {"messages": [...]}}``) or a ``CheckpointTuple`` (``.checkpoint``), and a
    ``get_state_history`` sequence (newest first, as LangGraph returns it).

The result is a record for the ``langgraph_msgs`` dialect: ``{"agent", "probe", "rep", "input", "trace", "output"}``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

_ROLE = {"human": "human", "user": "human", "ai": "ai", "assistant": "ai", "AIMessageChunk": "ai",
         "tool": "tool", "function": "tool", "system": "system"}


def _get(m: Any, key: str, default: Any = None) -> Any:
    if isinstance(m, dict):
        return m.get(key, default)
    return getattr(m, key, default)


def _unwrap(m: Any) -> Any:
    if isinstance(m, dict):
        if "lc" in m and isinstance(m.get("kwargs"), dict):
            kw = dict(m["kwargs"])
            ident = m.get("id") or []
            kw.setdefault("type", (ident[-1] if ident else "").replace("Message", "").lower() or "ai")
            return kw
        if isinstance(m.get("data"), dict) and "type" in m:
            return {**m["data"], "type": m["type"]}
    return m


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # content blocks
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return "" if content is None else str(content)


def _calls(m: Any) -> list[dict]:
    out = []
    for c in _get(m, "tool_calls") or []:
        args = _get(c, "args")
        if args is None and isinstance(_get(c, "function"), dict):  # OpenAI-style raw call
            args = c["function"].get("arguments")
            c = {"name": c["function"].get("name"), "id": _get(c, "id")}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {"input": args}
        out.append({"name": _get(c, "name", "") or "", "args": args or {}, "id": _get(c, "id")})
    return out


def from_messages(messages: Iterable[Any]) -> list[dict]:
    """Convert a LangChain / LangGraph message list into ``langgraph_msgs`` trace items (system messages dropped)."""
    trace: list[dict] = []
    for raw in messages:
        m = _unwrap(raw)
        role = _ROLE.get(str(_get(m, "type") or _get(m, "role") or "ai"), "ai")
        if role == "system":
            continue
        item: dict = {"role": role, "content": _text(_get(m, "content"))}
        calls = _calls(m) if role == "ai" else []
        if calls and item["content"].strip():  # the model's text beside its tool calls is their stated rationale
            for c in calls:
                c.setdefault("reason", item["content"].strip())
        if calls:
            item["tool_calls"] = calls
        if role == "tool" and _get(m, "tool_call_id"):
            item["tool_call_id"] = _get(m, "tool_call_id")
        trace.append(item)
    return trace


def from_stream_events(events: Iterable[dict]) -> list[dict]:
    """Convert ``astream_events(version="v2")`` dicts into ``langgraph_msgs`` trace items.

    Only completed model turns and tool runs are used; streaming chunks are ignored. The first human input is taken
    from the root ``on_chain_start`` event when present.
    """
    trace: list[dict] = []
    for e in events:
        kind, data = e.get("event"), e.get("data") or {}
        if kind == "on_chain_start" and not trace and not e.get("parent_ids"):
            inp = data.get("input")
            msgs = inp.get("messages") if isinstance(inp, dict) else None
            if msgs:
                trace.extend(t for t in from_messages(msgs) if t["role"] == "human")
            elif isinstance(inp, str):
                trace.append({"role": "human", "content": inp})
        elif kind == "on_chat_model_end":
            trace.extend(from_messages([data.get("output")]) if data.get("output") is not None else [])
        elif kind == "on_tool_start" and not any(c.get("name") == e.get("name") for t in trace[-1:]
                                                 for c in t.get("tool_calls", [])):
            trace.append({"role": "ai", "content": "", "tool_calls": [{"name": e.get("name", ""),
                                                                     "args": data.get("input") or {}}]})
        elif kind == "on_tool_end":
            out = data.get("output")
            content = _get(_unwrap(out), "content", out) if not isinstance(out, str) else out
            trace.append({"role": "tool", "content": _text(content) if not isinstance(content, (dict, list))
                          else json.dumps(content, sort_keys=True)})
    return trace


def _state_messages(obj: Any, key: str = "messages") -> list | None:
    """Find the message list inside a LangGraph state, snapshot, checkpoint or checkpoint tuple."""
    for attr in ("values", "checkpoint"):  # StateSnapshot.values / CheckpointTuple.checkpoint
        inner = _get(obj, attr)
        if inner is not None and not callable(inner):
            return _state_messages(inner, key)
    if isinstance(obj, dict):
        if isinstance(obj.get("channel_values"), dict):
            return _state_messages(obj["channel_values"], key)
        msgs = obj.get(key)
        return list(msgs) if isinstance(msgs, (list, tuple)) else None
    return None


def _dedupe(messages: list) -> list:
    """Drop repeated messages with the same ``id`` (the add_messages reducer can surface a message twice)."""
    seen, out = set(), []
    for m in messages:
        mid = _get(_unwrap(m), "id")
        if isinstance(mid, str) and mid:
            if mid in seen:
                continue
            seen.add(mid)
        out.append(m)
    return out


def from_state(state: Any, key: str = "messages") -> list[dict]:
    """Convert a LangGraph state / StateSnapshot / checkpoint / CheckpointTuple into ``langgraph_msgs`` trace items.

    ``key`` names the state channel holding messages (``"messages"`` for ``MessagesState``). Raises ``ValueError`` when
    no message list is found, so a wrong key fails loudly rather than producing an empty trace.
    """
    msgs = _state_messages(state, key)
    if msgs is None:
        raise ValueError(f"no message list under {key!r} in the LangGraph state or checkpoint")
    return from_messages(_dedupe(msgs))


def from_state_history(history: Iterable[Any], key: str = "messages") -> list[dict]:
    """Use the latest checkpoint of a ``get_state_history`` sequence (LangGraph yields newest first).

    Snapshots without a message list (e.g. the empty input checkpoint) are skipped; the newest with messages wins.
    """
    for snap in history:
        if _state_messages(snap, key):
            return from_state(snap, key)
    raise ValueError(f"no checkpoint in the history has messages under {key!r}")


def to_record(trace: list[dict], agent: str, probe: str = "run", rep: int = 0, output: dict | None = None) -> dict:
    """Wrap trace items as one native record for ``agentest std import`` with a ``langgraph_msgs`` mapping."""
    first = next((t["content"] for t in trace if t["role"] == "human"), "")
    final = next((t["content"] for t in reversed(trace) if t["role"] == "ai" and not t.get("tool_calls")), "")
    return {"agent": agent, "probe": probe, "rep": rep, "input": first, "trace": trace,
            "output": {"final_answer": final, **(output or {})}}
