"""Map a serialized Semantic Kernel Python 1.47.0 ChatHistory to an agentest Episode."""

import json

from agentest.standards.episode import Message
from agentest.standards.importers import NativeLogError


def _arguments(value):
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {"raw": value}
    if isinstance(value, dict):
        return value
    return {"value": value}


def _kernel_error(result):
    # kernel.py returns these SDK diagnostics as ordinary FunctionResultContent strings.
    return isinstance(result, str) and (
        result.startswith((
            "An error occurred while invoking the function ",
            "The tool call arguments are malformed. Arguments must be in JSON format.",
        ))
        or (result.startswith("The tool call with name `") and "is not part of the provided tools" in result)
        or (result.startswith(("Missing required argument(s):", "Received unexpected argument(s):"))
            and result.endswith("Please revise the arguments to match the function signature."))
        or (result.startswith("There are `") and result.endswith("Please provide the required arguments and try again."))
    )


def to_trace(raw: dict, ep) -> None:
    history = raw.get("history")
    if not isinstance(history, dict) or not isinstance(history.get("messages"), list):
        raise NativeLogError("history must contain the messages array from ChatHistory.serialize()")

    pending = {}
    for message in history["messages"]:
        role = message["role"]
        items = message["items"]
        if role == "assistant" and items and all(item["content_type"] == "function_call" for item in items):
            ep.say("")  # A tool-call-only assistant message still records a model turn.
        for item in items:
            kind = item["content_type"]
            if kind == "text":
                ep.messages.append(Message(role, item["text"]))
            elif kind == "function_call":
                call_id = item.get("call_id") or item.get("id") or ""
                function = item.get("function_name", "")
                plugin = item.get("plugin_name")
                name = item.get("name") or (f"{plugin}-{function}" if plugin else function)
                call = ep.add_tool(name, arguments=_arguments(item.get("arguments")), call_id=call_id)
                if call_id:
                    if call_id in pending:
                        raise NativeLogError("duplicate outstanding function call ID in Semantic Kernel history")
                    pending[call_id] = call
            elif kind == "function_result":
                result = item.get("result")
                exception = item.get("metadata", {}).get("exception")
                if isinstance(result, str):
                    ep.messages.append(Message("tool", result))
                call = pending.pop(item.get("call_id") or item.get("id"), None)
                if call is not None:
                    call.result = result if result is not None else exception
                    call.error = bool(exception) or _kernel_error(result)
