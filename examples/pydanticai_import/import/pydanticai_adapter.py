"""Map a recorded Pydantic AI message history to an agentest Episode.

Used by ``agentest std import --map examples/pydanticai_import/import/map.json``: the map selects
``"dialect": "file:pydanticai_adapter.py"`` and agentest loads this file. Each native record holds the
run's message history as Pydantic AI serialises it (``result.all_messages_json()``, or
``ModelMessagesTypeAdapter.dump_python(result.all_messages(), mode="json")``). This file only maps
fields, so it needs no ``pydantic-ai`` install, and it decides no verdicts.

Written against Pydantic AI 2.75.0 (``pydantic-ai-slim==2.75.0``): a message is a ``ModelRequest``
(``kind: "request"``) or a ``ModelResponse`` (``kind: "response"``) with a ``parts`` list, and each
part has a ``part_kind``. A ``tool-call`` part has ``tool_name``, ``args`` (an object or a JSON string)
and ``tool_call_id``; its ``tool-return`` part has the same ``tool_call_id``, the ``content`` and an
``outcome`` (``success``, ``failed``, ``denied``, ``interrupted`` or ``retried``). Older 1.x histories
report a rejected call as a ``retry-prompt`` part instead; both are read.
"""

import json

from agentest.standards.episode import Message

OUTPUT_TOOL = "final_result"  # Pydantic AI's default output tool name (``final_result`` or ``final_result_<Type>``)
FAILED = ("failed", "retried")  # outcomes that reach the model as an error
CALLS = ("tool-call", "builtin-tool-call")
RETURNS = ("tool-return", "builtin-tool-return")


def _arguments(value):
    """``args`` is a dict or a JSON string, depending on the provider; keep scalars and bad JSON."""
    if isinstance(value, str):
        try:
            value = json.loads(value) if value.strip() else None
        except ValueError:
            return {"raw": value}
    if isinstance(value, dict):
        return value
    return {} if value is None else {"value": value}


def _prompt(content) -> str:
    """``UserPromptPart.content`` is a string or a list of strings and media items; keep the text."""
    if isinstance(content, str):
        return content
    texts = [c if isinstance(c, str) else c.get("content", "") for c in content or []
             if isinstance(c, str) or (isinstance(c, dict) and c.get("kind") == "text-content")]
    return "\n".join(t for t in texts if isinstance(t, str))


def _is_output_tool(name) -> bool:
    return isinstance(name, str) and (name == OUTPUT_TOOL or name.startswith(OUTPUT_TOOL + "_"))


def to_trace(raw: dict, ep) -> None:
    calls = {}
    for message in raw.get("trace") or []:
        if not isinstance(message, dict):
            continue
        for part in message.get("parts") or []:
            if not isinstance(part, dict):
                continue
            kind, name, cid = part.get("part_kind"), part.get("tool_name"), str(part.get("tool_call_id") or "")
            if kind == "user-prompt":
                text = _prompt(part.get("content"))
                if text and text != ep.input:  # the run input already opens the first user turn
                    ep.messages.append(Message("user", text))
            elif kind == "text" and message.get("kind") == "response":
                if part.get("content"):
                    ep.say(str(part["content"]))
            elif kind in CALLS and _is_output_tool(name):
                ep.say(json.dumps(_arguments(part.get("args")), ensure_ascii=False))  # structured output is the reply
            elif kind in CALLS:
                calls[cid] = ep.add_tool(str(name or ""), arguments=_arguments(part.get("args")), call_id=cid)
            elif kind in RETURNS and cid in calls:
                calls[cid].result = part.get("content")
                calls[cid].error = part.get("outcome", "success") in FAILED
            elif kind == "retry-prompt" and cid in calls:  # 1.x: the call was rejected and the model is asked again
                calls[cid].result = part.get("content")
                calls[cid].error = True
            # system-prompt, thinking, file and other parts are neither replies nor tool evidence
