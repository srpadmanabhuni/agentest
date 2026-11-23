"""Map Haystack 3.5 ChatMessage.to_dict records to Agentest Episodes.

This is a per-log-format adapter. It reads serialized message dictionaries only;
Haystack itself is not imported or required.
"""
import json


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
    """Convert one single-turn Agent.run() message list into an Agentest Episode."""
    trace = raw.get("trace") or []
    if not isinstance(trace, list):
        raise ValueError("Haystack trace must be a list of serialized ChatMessage objects")
    if any(not isinstance(message, dict) for message in trace):
        raise ValueError("each Haystack message must be an object from ChatMessage.to_dict()")

    # The native-log envelope already carries the user input. Keep this mapper
    # single-turn and explicit rather than silently flattening conversation history.
    user_inputs = [
        _text(message.get("content"))
        for message in trace
        if message.get("role") == "user" and _text(message.get("content"))
    ]
    if len(user_inputs) > 1:
        raise ValueError("multiple Haystack user messages are not supported; export a complete OTLP trace instead")
    if user_inputs:
        if ep.input and ep.input != user_inputs[0]:
            raise ValueError("top-level input does not match the Haystack user message")
        if not ep.input:
            ep.input = user_inputs[0]

    if any(
        message.get("role") == "system" and _text(message.get("content"))
        for message in trace
    ):
        raise ValueError("Haystack system messages are not represented by this mapper; use complete OTLP instrumentation")

    calls = []
    calls_by_id = {}
    resolved = set()

    for message in trace:
        role = message.get("role")
        actor = message.get("name") or ""
        content = _parts(message.get("content"))

        if role in ("user", "system"):
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
                if "tool_call" not in part:
                    # Reasoning, images and files are deliberately not exported.
                    continue
                tool = part["tool_call"]
                if not isinstance(tool, dict):
                    raise ValueError("Haystack tool_call content must be an object")
                name = tool.get("tool_name")
                arguments = tool.get("arguments")
                if not isinstance(name, str) or not name:
                    raise ValueError("Haystack ToolCall is missing tool_name")
                if not isinstance(arguments, dict):
                    raise ValueError(f"Haystack ToolCall {name!r} arguments must be an object")
                call_id = tool.get("id")
                if call_id is not None and str(call_id) in calls_by_id:
                    raise ValueError(f"duplicate Haystack ToolCall id: {call_id!r}")

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

            # Preserve assistant text alongside tool calls; empty call-only
            # assistant messages retain their place in the source sequence.
            if text_parts or had_tool_call:
                ep.say("".join(text_parts), actor=actor)
            continue

        if role == "tool":
            result_parts = [
                part["tool_call_result"]
                for part in content
                if isinstance(part, dict) and "tool_call_result" in part
            ]
            if not result_parts:
                raise ValueError("Haystack tool message has no tool_call_result content")

            for result_part in result_parts:
                if not isinstance(result_part, dict):
                    raise ValueError("Haystack tool_call_result content must be an object")
                origin = result_part.get("origin")
                if not isinstance(origin, dict):
                    raise ValueError("Haystack ToolCallResult is missing its origin ToolCall")
                call_id = origin.get("id")
                tool_name = origin.get("tool_name") or message.get("name") or ""

                if call_id is not None:
                    call_index = calls_by_id.get(str(call_id))
                    if call_index is None:
                        raise ValueError(f"Haystack ToolCallResult references unknown ToolCall id: {call_id!r}")
                else:
                    origin_arguments = origin.get("arguments")
                    matches = [
                        index
                        for index, candidate in enumerate(calls)
                        if index not in resolved
                        and candidate.name == tool_name
                        and (
                            not isinstance(origin_arguments, dict)
                            or candidate.arguments == origin_arguments
                        )
                    ]
                    if len(matches) != 1:
                        raise ValueError(
                            "Haystack ToolCallResult without an id must match exactly one unresolved "
                            f"ToolCall (tool_name={tool_name!r}, matches={len(matches)})"
                        )
                    call_index = matches[0]

                if call_index in resolved:
                    raise ValueError(f"duplicate Haystack ToolCallResult for ToolCall id: {call_id!r}")

                call = calls[call_index]
                # Keep visible text only; image/file parts may contain large or sensitive payloads.
                call.result = _result_text(result_part.get("result"))
                call.error = bool(result_part.get("error"))
                resolved.add(call_index)
            continue

        raise ValueError(f"unsupported Haystack ChatMessage role: {role!r}")
