"""Map Haystack 3.5 ChatMessage.to_dict records to Agentest Episodes.

This is a per-log-format adapter. It reads serialized message dictionaries only;
Haystack itself is not imported or required.
"""
import json

from agentest.standards.episode import Message


def _parts(content):
    if content is None:
        return []
    if isinstance(content, str):  # pre-2.9 ChatMessage serialization
        return [{"text": content}]
    if not isinstance(content, list):
        raise ValueError("Haystack ChatMessage content must be a list or string")
    return content


def _text(content):
    return "".join(
        part["text"]
        for part in _parts(content)
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )


def _result_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(
            part["text"]
            for part in value
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ) or "[non-text tool result omitted]"
    if value is None:
        return ""
    if isinstance(value, (dict, int, float, bool)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def to_trace(raw: dict, ep) -> None:
    """Convert one Agent.run() message list into the Episode consumed by Agentest."""
    trace = raw.get("trace") or []
    if not isinstance(trace, list):
        raise ValueError("Haystack trace must be a list of serialized ChatMessage objects")

    calls = []
    calls_by_id = {}
    resolved = set()

    for message in trace:
        if not isinstance(message, dict):
            raise ValueError("each Haystack message must be an object from ChatMessage.to_dict()")

        role = message.get("role")
        actor = message.get("name") or ""
        content = _parts(message.get("content"))

        if role in ("user", "system"):
            text = _text(content)
            if text:
                ep.messages.append(Message(role, text, actor=actor))
            continue

        if role == "assistant":
            text_parts = []
            had_tool_call = False
            for part in content:
                if not isinstance(part, dict):
                    continue
                if isinstance(part.get("text"), str):
                    text_parts.append(part["text"])
                    continue
                tool = part.get("tool_call")
                if not isinstance(tool, dict):
                    # Reasoning, images and files are deliberately not exported.
                    continue
                name = tool.get("tool_name")
                arguments = tool.get("arguments")
                if not isinstance(name, str) or not name:
                    raise ValueError("Haystack ToolCall is missing tool_name")
                if not isinstance(arguments, dict):
                    raise ValueError(f"Haystack ToolCall {name!r} arguments must be an object")
                call_id = tool.get("id")
                call = ep.add_tool(
                    name,
                    arguments,
                    actor=actor,
                    call_id=str(call_id) if call_id is not None else "",
                )
                call_index = len(calls)
                calls.append(call)
                if call_id is not None:
                    calls_by_id[str(call_id)] = call_index
                had_tool_call = True

            # Preserve empty assistant messages that only contain tool calls,
            # matching the framework's message sequence.
            if text_parts or had_tool_call:
                ep.say("".join(text_parts), actor=actor)
            continue

        if role == "tool":
            for part in content:
                if not isinstance(part, dict):
                    continue
                result_part = part.get("tool_call_result")
                if not isinstance(result_part, dict):
                    continue
                origin = result_part.get("origin") or {}
                call_id = origin.get("id")
                tool_name = origin.get("tool_name") or message.get("name") or ""

                call_index = calls_by_id.get(str(call_id)) if call_id is not None else None
                if call_index is None:
                    origin_arguments = origin.get("arguments")
                    call_index = next(
                        (
                            index
                            for index, candidate in enumerate(calls)
                            if index not in resolved
                            and candidate.name == tool_name
                            and (
                                not isinstance(origin_arguments, dict)
                                or candidate.arguments == origin_arguments
                            )
                        ),
                        None,
                    )
                if call_index is None:
                    raise ValueError(
                        f"Haystack ToolCallResult has no matching ToolCall "
                        f"(id={call_id!r}, tool_name={tool_name!r})"
                    )

                call = calls[call_index]
                # Keep visible text only; image/file parts may contain large or sensitive payloads.
                result = _result_text(result_part.get("result"))
                call.result = result
                call.error = bool(result_part.get("error"))
                resolved.add(call_index)
                ep.messages.append(Message("tool", result, actor=actor))
            continue

        raise ValueError(f"unsupported Haystack ChatMessage role: {role!r}")
