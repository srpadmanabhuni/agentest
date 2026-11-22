"""Map a recorded Vercel AI SDK UIMessage stream to an agentest Episode.

Used by ``agentest std import --map examples/ai_sdk_import/import/map.json``: the map selects
``"dialect": "file:ai_sdk.py"`` and agentest loads this file. The native records hold `UIMessage`
objects (``id``, ``role``, ``parts``) as an AI SDK chat store would save them; this file only
maps fields, so it needs no Node and no ``ai`` package, and it decides no verdicts.

Written against AI SDK 7 (``ai@7.0.179``): a tool part has ``type: "tool-<name>"``, ``toolCallId``,
``state``, ``input`` and either ``output`` (``output-available``) or ``errorText`` (``output-error``).
"""

from agentest.standards.episode import Message

TOOL = "tool-"


def _arguments(value):
    """ToolUIPart.input is a JSON object; keep it as-is, without losing scalar inputs."""
    if isinstance(value, dict):
        return value
    return {} if value is None else {"value": value}


def to_trace(raw: dict, ep) -> None:
    for message in raw.get("trace") or []:
        if not isinstance(message, dict):
            continue
        role = message.get("role", "assistant")
        for part in message.get("parts") or []:
            if not isinstance(part, dict):
                continue
            kind = part.get("type")
            if kind == "text":
                text = str(part.get("text", ""))
                if role == "user":
                    ep.messages.append(Message("user", text))
                elif role == "assistant":
                    ep.say(text)
                continue
            if not isinstance(kind, str) or not kind.startswith(TOOL):
                continue  # reasoning / data parts are neither replies nor tool evidence
            failed = part.get("state") == "output-error"
            ep.add_tool(kind[len(TOOL):], arguments=_arguments(part.get("input")),
                        result=part.get("errorText") if failed else part.get("output"),
                        error=failed, call_id=str(part.get("toolCallId") or ""))
