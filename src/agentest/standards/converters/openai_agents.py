"""OpenAI Agents SDK converter (issue #1): run items -> native record for the ``openai_agents`` dialect.

Accepted inputs, all read without importing the SDK:
  * ``RunResult.new_items`` objects (duck typed: ``.type`` in ``message_output_item`` / ``tool_call_item`` /
    ``tool_call_output_item`` / ``handoff_call_item`` / ``handoff_output_item``, with ``.raw_item``, ``.agent``,
    ``.output``, ``.source_agent`` / ``.target_agent``), or the same as dicts;
  * ``RunResult.to_input_list()`` items (Responses-API dicts: ``{"role": ..., "content": ...}`` messages,
    ``{"type": "function_call", "name", "arguments", "call_id"}``, ``{"type": "function_call_output", "call_id",
    "output"}``).

The result is ``{"agent", "probe", "rep", "input", "trace", "output"}``; ``trace`` uses the dialect's item types
(``tool_call_item`` with ``tool``/``args``/``agent``, ``tool_call_output_item`` with ``output``,
``handoff_output_item`` with ``agent``/``to``) plus ``message_output_item`` items with ``role``/``content``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any


def _get(m: Any, key: str, default: Any = None) -> Any:
    if isinstance(m, dict):
        return m.get(key, default)
    return getattr(m, key, default)


def _name(agent: Any) -> str:
    if agent is None:
        return ""
    return agent if isinstance(agent, str) else str(_get(agent, "name", "") or "")


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # output_text / input_text blocks
        return "".join(str(_get(b, "text", "") or "") if not isinstance(b, str) else b for b in content)
    return "" if content is None else str(content)


def _args(a: Any) -> Any:
    if isinstance(a, str):
        try:
            return json.loads(a)
        except ValueError:
            return {"input": a}
    return a or {}


def from_items(items: Iterable[Any], agent: str = "") -> list[dict]:
    """Convert run items (``new_items`` objects/dicts or ``to_input_list()`` dicts) into dialect trace items."""
    trace: list[dict] = []
    for it in items:
        ty, raw = _get(it, "type"), _get(it, "raw_item")
        who = _name(_get(it, "agent")) or agent
        if raw is not None and ty in ("message_output_item", "tool_call_item", "tool_call_output_item",
                                      "handoff_call_item", "handoff_output_item", "reasoning_item"):
            if ty == "message_output_item":
                trace.append({"type": ty, "role": "assistant", "content": _text(_get(raw, "content")), "agent": who})
            elif ty == "tool_call_item":
                trace.append({"type": ty, "tool": _get(raw, "name", "") or "", "args": _args(_get(raw, "arguments")),
                              "agent": who, "call_id": _get(raw, "call_id")})
            elif ty == "tool_call_output_item":
                trace.append({"type": ty, "output": _get(it, "output", _get(raw, "output")), "agent": who,
                              "call_id": _get(raw, "call_id")})
            elif ty == "handoff_output_item":
                trace.append({"type": ty, "agent": _name(_get(it, "source_agent")) or who,
                              "to": _name(_get(it, "target_agent"))})
            continue  # handoff_call_item / reasoning_item carry nothing the dialect scores
        if ty == "function_call":
            trace.append({"type": "tool_call_item", "tool": _get(it, "name", "") or "",
                          "args": _args(_get(it, "arguments")), "agent": agent, "call_id": _get(it, "call_id")})
        elif ty == "function_call_output":
            trace.append({"type": "tool_call_output_item", "output": _get(it, "output"), "agent": agent,
                          "call_id": _get(it, "call_id")})
        elif ty in (None, "message") and _get(it, "role"):
            trace.append({"type": "message_output_item", "role": _get(it, "role"),
                          "content": _text(_get(it, "content")), "agent": agent})
        elif ty in ("tool_call_item", "tool_call_output_item", "handoff_output_item", "message_output_item"):
            trace.append(dict(it))  # already in dialect shape
    return trace


def to_record(trace: list[dict], agent: str, probe: str = "run", rep: int = 0, output: dict | None = None,
              input: str | None = None, final_output: Any = None) -> dict:
    """Wrap trace items as one native record for ``agentest std import --dialect openai_agents``.

    ``input`` defaults to the first user message; ``final_output`` (``RunResult.final_output``) to the last assistant
    message.
    """
    first = input if input is not None else next(
        (t["content"] for t in trace if t.get("type") == "message_output_item" and t.get("role") == "user"), "")
    final = final_output if final_output is not None else next(
        (t["content"] for t in reversed(trace) if t.get("type") == "message_output_item"
         and t.get("role") == "assistant"), "")
    return {"agent": agent, "probe": probe, "rep": rep, "input": first, "trace": trace,
            "output": {"final_answer": final if isinstance(final, str) else json.dumps(final, default=str),
                       **(output or {})}}
