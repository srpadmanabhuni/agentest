"""Map a recorded Agno run (its ``RunOutput.messages``) to an agentest Episode.

Used by ``agentest std import --map examples/agno_import/import/map.json``: the map selects
``"dialect": "file:agno_adapter.py"`` and agentest loads this file. Each native record keeps the run's messages as
``[m.to_dict() for m in run_output.messages]``; this file only maps fields, so it needs no ``agno`` package, makes
no model or network call, and decides no verdicts.

Written against Agno 3.2.1 (``agno.models.message.Message``): ``role`` is ``system``, ``user``, ``assistant`` or
``tool``; an assistant message carries ``tool_calls`` (``{"id", "type": "function", "function": {"name",
"arguments"}}``, arguments as a JSON string); a tool message carries the result in ``content`` plus
``tool_call_id``, ``tool_name``, ``tool_args`` and ``tool_call_error``. Messages with ``from_history: true`` were
replayed from earlier runs of the session and are skipped.
"""

import json

from agentest.standards.episode import Message


def _arguments(value) -> dict:
    """Tool arguments are a JSON string in ``tool_calls`` and a dict in ``tool_args``; keep scalars too."""
    if isinstance(value, str):
        try:
            value = json.loads(value) if value.strip() else {}
        except ValueError:
            return {"raw": value}
    if isinstance(value, dict):
        return value
    return {} if value is None else {"value": value}


def _text(content) -> str:
    """Message content is a string, or a list of content parts with ``text``."""
    if isinstance(content, list):
        return "".join(str(p.get("text", "")) if isinstance(p, dict) else str(p) for p in content)
    return "" if content is None else str(content)


def to_trace(raw: dict, ep) -> None:
    calls = {}
    for message in raw.get("trace") or []:
        if not isinstance(message, dict) or message.get("from_history"):
            continue
        role = message.get("role")
        text = _text(message.get("content"))
        if role == "user":
            if text != ep.input:  # the run input already opens the first user turn
                ep.messages.append(Message("user", text))
        elif role == "assistant":
            if text.strip():
                ep.say(text, actor=str(message.get("name") or ""))
            for c in message.get("tool_calls") or []:
                if not isinstance(c, dict):
                    continue
                fn = c.get("function") or {}
                call_id = str(c.get("id") or "")
                call = ep.add_tool(str(fn.get("name") or ""), arguments=_arguments(fn.get("arguments")), call_id=call_id)
                if call_id:
                    calls[call_id] = call
        elif role == "tool":
            call_id = str(message.get("tool_call_id") or "")
            call = calls.pop(call_id, None)
            if call is None:  # a tool message without its assistant request still names the tool and its arguments
                call = ep.add_tool(str(message.get("tool_name") or ""), arguments=_arguments(message.get("tool_args")),
                                   call_id=call_id)
            call.result = message.get("content")
            call.error = bool(message.get("tool_call_error"))
        # system messages are instructions, not replies
