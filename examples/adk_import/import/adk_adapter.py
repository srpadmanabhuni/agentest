"""Translate recorded Google ADK session events into Agentest episodes.

Uses only recorded event data. No ADK runtime, network calls, or model calls.
"""

def to_trace(raw: dict, ep) -> None:
    pending = {}

    for event in raw.get("trace") or []:
        if not isinstance(event, dict):
            continue

        author = str(event.get("author") or "")
        content = event.get("content") or {}
        parts = content.get("parts") or []

        if not isinstance(parts, list):
            continue

        for part in parts:
            if not isinstance(part, dict):
                continue

            text = part.get("text")
            if isinstance(text, str) and text.strip():
                if author not in ("user", "system"):
                    ep.say(text, actor=author)

            function_call = part.get("functionCall") or part.get("function_call")
            if isinstance(function_call, dict):
                name = str(function_call.get("name") or "")
                if not name:
                    continue

                call = ep.add_tool(
                    name=name,
                    arguments=function_call.get("args") or {},
                    actor=author,
                    call_id=str(function_call.get("id") or ""),
                )
                call_id = str(function_call.get("id") or "")
                if call_id:
                    pending[call_id] = call
                elif name:
                    pending.setdefault(name, []).append(call)

            function_response = (
                part.get("functionResponse")
                or part.get("function_response")
            )
            if isinstance(function_response, dict):
                call_id = str(function_response.get("id") or "")
                name = str(function_response.get("name") or "")
                call = pending.get(call_id) if call_id else None

                if call is None and name:
                    candidates = pending.get(name)
                    if isinstance(candidates, list) and candidates:
                        call = candidates.pop(0)

                if call is not None:
                    result = function_response.get("response")
                    call.result = result
                    call.error = (
                        isinstance(result, dict) and bool(result.get("error"))
                    ) or bool(event.get("error"))