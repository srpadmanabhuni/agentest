"""Import native agent logs into OTLP/JSON (OpenTelemetry GenAI spans): ``agentest std import``.

This is the only framework-specific code, and it is pure mapping, driven by data: a *dialect* (how a framework
writes its log) and a *mapping* file (where the facts sit in a native record). It computes no verdicts. Agents that
emit OpenTelemetry GenAI spans themselves need none of this.

Dialects:
  steps            plain Python / LangGraph node logs / LlamaIndex steps / CrewAI task list
  openai_agents    OpenAI Agents SDK RunItems (tool_call_item, handoff_output_item, ...)
  langgraph_msgs   LangGraph message list (role, content, tool_calls)
  autogen          AutoGen AgentChat events (ToolCallRequestEvent / FunctionCall reprs)
  n8n              n8n execution JSON (one execution is one turn; sessionId joins a conversation)
  events           seq/kind event log (llm/tool/write/message/route)
  file:mod.py      your own ``to_trace(raw, ep)`` mapping function

Mapping file (JSON)::

  {"dialect": "events", "framework": "OpenAI Agents SDK",
   "observations": {"final_answer": ["output.final"], "executed": ["output.executed"], "pending": ["output.pending"],
                    "approvals": ["output.approval_audit"], "state_diff": [], "citations": [], "outputs": [], "evaluation": []},
   "labels": {"inputs": {"<input id>": {"families": ["injection"], "injected": ["..."]}}, "canaries": ["..."],
              "relations": [{"relation": "declared", "members": ["a", "b"], "kind": "same"}]}}

``labels`` are test-harness labels (what kind of stimulus each recorded input was); they are written to the root
span as ``agentest.input.families``, ``agentest.input.injected``, ``agentest.test.canaries`` and
``agentest.input.relations``.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from agentest.standards.episode import Approval, Episode, Handoff, Message, StateChange, ToolCall
from agentest.standards.expr import get_path

_FC = re.compile(r"FunctionCall\(id='([^']*)', arguments='((?:[^'\\]|\\.)*)', name='([^']*)'\)")


def _args(x: Any) -> dict:
    if isinstance(x, dict):
        return x
    if isinstance(x, str):
        for f in (json.loads, ast.literal_eval):
            try:
                v = f(x)
                return v if isinstance(v, dict) else {"value": v}
            except Exception:
                pass
        return {"raw": x}
    return {} if x is None else {"value": x}


def _autogen_calls(content: str, actor: str) -> list[ToolCall]:
    out = []
    for cid, a, name in _FC.findall(content or ""):
        a = a.replace("\\'", "'")
        out.append(ToolCall(name=name, arguments=_args(a), actor=actor, call_id=cid))
    return out


def _steps(tr: list, ep: Episode) -> None:
    for t in tr:
        if not isinstance(t, dict):
            continue
        name = t.get("step") or t.get("node") or t.get("agent") or ""
        if "sources" in t and not t.get("log"):  # a retrieval step (LlamaIndex/LangGraph) is identified by its sources, not its name
            ep.tool_calls.append(ToolCall(name=name or "retrieve", arguments={}, result=t.get("sources")))
        elif t.get("agent") and "output" in t:  # CrewAI task output
            ep.messages.append(Message("assistant", str(t["output"]), actor=t["agent"]))
        for n in t.get("log", []) or []:  # LangGraph durable node log
            if isinstance(n, dict) and n.get("node"):
                ep.tool_calls.append(ToolCall(name=n["node"], arguments={k: v for k, v in n.items() if k != "node"}))


def _openai_agents(tr: list, ep: Episode) -> None:
    for t in tr:
        ty = t.get("type")
        if ty == "tool_call_item":
            ep.tool_calls.append(ToolCall(name=t.get("tool", ""), arguments=_args(t.get("args")), actor=t.get("agent", "")))
        elif ty == "tool_call_output_item" and ep.tool_calls:
            ep.tool_calls[-1].result = t.get("output")
        elif ty == "handoff_output_item":
            ep.handoffs.append(Handoff(t.get("agent", ""), t.get("to", "")))


def _langgraph_msgs(tr: list, ep: Episode) -> None:
    role = {"human": "user", "ai": "assistant", "tool": "tool"}
    for t in tr:
        if "role" not in t:
            continue
        ep.messages.append(Message(role.get(t["role"], "assistant"), str(t.get("content", ""))))
        for c in t.get("tool_calls", []) or []:
            ep.tool_calls.append(ToolCall(name=c.get("name", ""), arguments=_args(c.get("args"))))
        if t["role"] == "tool" and ep.tool_calls and ep.tool_calls[-1].result is None:
            ep.tool_calls[-1].result = t.get("content")


def _autogen(tr: list, ep: Episode) -> None:
    for t in tr:
        ty, src, content = t.get("type"), t.get("source", ""), t.get("content", "")
        if ty == "ToolCallRequestEvent":
            ep.tool_calls += _autogen_calls(content, src)
        elif ty == "TextMessage":
            ep.messages.append(Message("user" if src == "user" else "assistant", str(content), actor=src))


class N8nImportError(ValueError):
    """An n8n execution log is not in the documented export shape, or its user text is not valid JSON."""


_EXEC_MARKS = ("data", "resultData", "runData", "workflowData", "workflowId")
_USER_KEYS = ("chatInput", "message", "text", "content", "input")


def _n8n_kind(node_type: str) -> str:
    """Classify an n8n node type string. Empty when the type is absent or not one of the AI node families."""
    s = str(node_type or "").rsplit(".", 1)[-1].lower()
    if not s:
        return ""
    if "chattrigger" in s:
        return "chat"
    if "memory" in s:
        return "memory"
    if s in {"agent", "agenttool"} or s.endswith("agent"):
        return "agent"
    if "lmchat" in s or "languagemodel" in s or "outputparser" in s or "embeddings" in s:
        return "model"
    if "tool" in s:
        return "tool"
    return ""


def _conn_items(blob: Any, *keys: str) -> list[dict]:
    """Items on an n8n connection (``data.main``, ``data.ai_tool``, ``inputOverride.ai_tool``, ...)."""
    if not isinstance(blob, dict):
        return []
    for key in keys:
        branches = blob.get(key)
        if not isinstance(branches, list):
            continue
        items = [item for branch in branches if isinstance(branch, list) for item in branch if isinstance(item, dict)]
        if items:
            return items
    return []


def _item_json(item: dict) -> dict:
    js = item.get("json")
    return js if isinstance(js, dict) else {}


def _literal_key(value: Any) -> str:
    """A session key already resolved to text. Expressions (``={{ ... }}``) are not a key."""
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if not isinstance(value, str):
        return ""
    s = value.strip()
    if not s or s.startswith("=") or "{{" in s:
        return ""
    return s


def _unwrap_user(value: Any, depth: int = 0) -> str:
    """User text out of an n8n chat payload.

    The Chat Trigger puts the turn in ``chatInput``. That value is sometimes the text itself and sometimes a JSON
    string (or object) shaped ``{"chatInput": ...}`` or a message (``role``/``type`` + ``content``, or a LangChain
    ``kwargs.content``). A string that starts a JSON value and does not parse is an error. A JSON object that is not
    one of those wrappers is the user's own text and is kept.
    """
    if depth > 8:
        raise N8nImportError("n8n user input is malformed: message nesting is too deep")
    if value is None:
        return ""
    if isinstance(value, str):
        s = value.strip()
        if s[:1] in "{[":
            try:
                parsed = json.loads(s)
            except json.JSONDecodeError as e:
                raise N8nImportError(f"n8n user input is malformed JSON: {e.msg}") from e
            if isinstance(parsed, (dict, list)):
                inner = _unwrap_user(parsed, depth + 1)
                return value if inner == "" else inner
        return value
    if isinstance(value, list):
        parts = []
        for part in value:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                piece = part.get("text", part.get("content"))
                if piece is None and isinstance(part.get("kwargs"), dict):
                    piece = part["kwargs"].get("content")
                if piece is not None:
                    parts.append(_unwrap_user(piece, depth + 1))
        return " ".join(p for p in parts if p)
    if isinstance(value, dict):
        if isinstance(value.get("kwargs"), dict) and value["kwargs"].get("content") not in (None, ""):
            return _unwrap_user(value["kwargs"]["content"], depth + 1)
        data = value.get("data")
        if isinstance(data, dict) and data.get("content") not in (None, "") and "chatInput" not in value:
            return _unwrap_user(data["content"], depth + 1)
        for key in _USER_KEYS:
            if value.get(key) not in (None, ""):
                return _unwrap_user(value[key], depth + 1)
        return ""
    return str(value)


def _iso_to_ns(text: str, field: str) -> int:
    """ISO-8601 timestamp (n8n ``startedAt`` / ``stoppedAt``) to unix nanoseconds, at millisecond resolution."""
    from datetime import datetime

    s = str(text).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        raise N8nImportError(f"n8n execution is malformed: {field} is not ISO-8601 ({e})") from e
    if dt.tzinfo is None:
        raise N8nImportError(f"n8n execution is malformed: {field} must include a timezone")
    return int(dt.timestamp() * 1000) * 1_000_000


def _ms_window(run: dict) -> tuple[int | None, int | None]:
    """n8n ``startTime`` and ``executionTime`` are milliseconds. Return unix nanoseconds, or None when absent."""
    st, dur = run.get("startTime"), run.get("executionTime")
    if isinstance(st, bool) or not isinstance(st, (int, float)):
        return None, None
    start = int(st) * 1_000_000
    if isinstance(dur, bool) or not isinstance(dur, (int, float)):
        return start, None
    return start, start + int(dur) * 1_000_000


def _run_failed(run: dict) -> bool:
    return str(run.get("executionStatus") or "").lower() in {"error", "crashed", "failed"} or bool(run.get("error"))


def _error_text(err: Any) -> str:
    if isinstance(err, dict):
        msg = err.get("message") or err.get("description")
        return str(msg) if msg else json.dumps(err, ensure_ascii=False, default=str)
    return str(err) if err else "tool error"


def _result_of(js: dict) -> Any:
    if "response" in js:
        return js["response"]
    if "output" in js and set(js) <= {"output", "text"}:
        return js["output"]
    if "text" in js and set(js) <= {"output", "text"}:
        return js["text"]
    return js or None


def _runs_of(run_data: dict, name: str) -> list[dict]:
    runs = run_data.get(name)
    if runs is None:
        return []
    if not isinstance(runs, list) or any(not isinstance(r, dict) for r in runs):
        raise N8nImportError(f"n8n execution is malformed: run data for {name!r} must be a list of objects")
    return runs


def _execution_result(raw: dict) -> dict | None:
    """The ``resultData`` object when ``raw`` is an n8n execution export, else None. Malformed exports raise."""
    if not any(k in raw for k in _EXEC_MARKS):
        return None
    data = raw.get("data", raw)
    if not isinstance(data, dict):
        raise N8nImportError("n8n execution is malformed: 'data' must be an object (unflattened execution JSON)")
    result = data.get("resultData") if "resultData" in data else data if "runData" in data else None
    if not isinstance(result, dict) or not isinstance(result.get("runData"), dict) or not result.get("runData"):
        raise N8nImportError("n8n execution is malformed: resultData.runData must be a non-empty object")
    return result


def _workflow_nodes(raw: dict) -> dict[str, dict]:
    wf = raw.get("workflowData")
    if wf is None:
        return {}
    if not isinstance(wf, dict):
        raise N8nImportError("n8n execution is malformed: workflowData must be an object")
    nodes = wf.get("nodes", [])
    if not isinstance(nodes, list) or any(not isinstance(n, dict) for n in nodes):
        raise N8nImportError("n8n execution is malformed: workflowData.nodes must be a list of objects")
    return {str(n.get("name")): n for n in nodes if n.get("name")}


def _shape_kind(runs: list[dict]) -> str:
    for run in runs:
        if _conn_items(run.get("data"), "ai_memory"):
            return "memory"
        if _conn_items(run.get("data"), "ai_languageModel"):
            return "model"
        for item in _conn_items(run.get("data"), "main"):
            js = _item_json(item)
            if "chatInput" in js or js.get("action") in ("sendMessage", "loadPreviousSession"):
                return "chat"
        if _conn_items(run.get("data"), "ai_tool") or _conn_items(run.get("inputOverride"), "ai_tool"):
            return "tool"
        for item in _conn_items(run.get("data"), "main"):
            js = _item_json(item)
            if "output" in js or "text" in js:
                return "agent"
    return "other"


def _chat_session(item: dict, node: dict | None) -> str:
    """Conversation id: the chat item's ``sessionId``, else the Chat Trigger's literal session key."""
    sid = item.get("sessionId")
    if sid not in (None, "") and not isinstance(sid, (dict, list)):
        return str(sid)
    params = (node or {}).get("parameters") if isinstance((node or {}).get("parameters"), dict) else {}
    options = params.get("options") if isinstance(params.get("options"), dict) else {}
    for candidate in (item.get("sessionKey"), params.get("sessionKey"), options.get("sessionKey")):
        got = _literal_key(candidate)
        if got:
            return got
    return ""


def _chat_item(runs: list[dict]) -> dict:
    found: dict = {}
    for run in runs:
        for item in _conn_items(run.get("data"), "main"):
            js = _item_json(item)
            if js.get("action") == "loadPreviousSession":
                continue
            if any(k in js for k in ("chatInput", "message", "text", "input")) or js.get("action") == "sendMessage":
                found = js
    if not found:
        raise N8nImportError("n8n execution is malformed: Chat Trigger output has no chatInput")
    return found


def _tool_result_calls(name: str, run: dict, actor: str) -> list[ToolCall]:
    inputs = [_item_json(i) for i in _conn_items(run.get("inputOverride"), "ai_tool", "main")]
    outputs = [_item_json(i) for i in _conn_items(run.get("data"), "ai_tool", "main")]
    failed = _run_failed(run)
    if not inputs and not outputs and not failed:
        return []
    start, end = _ms_window(run)
    n = max(len(inputs), len(outputs), 1)
    calls = []
    for i in range(n):
        args = inputs[i] if i < len(inputs) else {}
        if i < len(outputs):
            result = _result_of(outputs[i])
        else:
            result = _error_text(run.get("error")) if failed else None
        if failed and result is None:
            result = _error_text(run.get("error"))
        calls.append(ToolCall(name=name, arguments=_args(args), result=result, actor=actor, error=failed, start_ns=start, end_ns=end))
    return calls


def _intermediate_steps(js: dict) -> list[tuple[str, Any, Any]]:
    steps = js.get("intermediateSteps") if isinstance(js.get("intermediateSteps"), list) else []
    out = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        action = step.get("action") if isinstance(step.get("action"), dict) else step
        name = action.get("tool") or action.get("name") or ""
        if not name:
            continue
        tool_input = action.get("toolInput", action.get("tool_input", action.get("args", {})))
        out.append((str(name), tool_input, step.get("observation", step.get("result"))))
    return out


def _n8n_execution(raw: dict, result: dict, ep: Episode) -> None:
    """One n8n execution (one chat turn) -> conversation id, unwrapped user text, assistant text, tool spans."""
    run_data = result["runData"]
    if not isinstance(run_data, dict):
        raise N8nImportError("n8n execution is malformed: resultData.runData must be a non-empty object")
    nodes = _workflow_nodes(raw)
    kinds: dict[str, str] = {}
    for name in run_data:
        runs = _runs_of(run_data, name)
        kind = _n8n_kind(str((nodes.get(name) or {}).get("type") or "")) or _shape_kind(runs)
        kinds[name] = kind
    chats = [name for name, kind in kinds.items() if kind == "chat"]
    if not chats:
        raise N8nImportError("n8n execution is malformed: no Chat Trigger output (sessionId / chatInput)")
    chat_name = chats[0]
    item = _chat_item(_runs_of(run_data, chat_name))
    text = _unwrap_user(item.get("chatInput", item.get("message", item.get("text", item.get("input")))))
    if not str(text).strip():
        raise N8nImportError("n8n execution is malformed: Chat Trigger chatInput is empty")
    ep.input = text
    ep.conversation = _chat_session(item, nodes.get(chat_name))
    agents = [name for name, kind in kinds.items() if kind == "agent"]
    last = result.get("lastNodeExecuted")
    agent_name = last if last in agents else (agents[-1] if agents else "")
    answer = ""
    steps: list[tuple[str, Any, Any]] = []
    agent_window = (None, None)
    if agent_name:
        for run in _runs_of(run_data, agent_name):
            agent_window = _ms_window(run) if _ms_window(run)[0] is not None else agent_window
            for node_item in _conn_items(run.get("data"), "main"):
                js = _item_json(node_item)
                if "output" in js:
                    answer = js["output"]
                elif "text" in js:
                    answer = js["text"]
                steps = _intermediate_steps(js) or steps
        if isinstance(answer, (dict, list)) or (isinstance(answer, str) and answer.strip()[:1] in "{["):
            try:
                answer = _unwrap_user(answer)
            except N8nImportError:
                answer = answer if isinstance(answer, str) else _text(answer)
        if answer not in ("", None):
            ep.final_answer = answer if isinstance(answer, str) else _text(answer)
            ep.messages.append(Message("assistant", ep.final_answer, actor=agent_name))
    calls: list[ToolCall] = []
    for name, kind in kinds.items():
        if kind != "tool":
            continue  # memory, model, chat and agent nodes are not tool calls
        for run in _runs_of(run_data, name):
            calls += _tool_result_calls(name, run, agent_name)
    seen: dict[str, int] = {}
    for c in calls:
        key = c.name + "\0" + json.dumps(c.arguments, sort_keys=True, default=str)
        seen[key] = seen.get(key, 0) + 1
    for name, tool_input, observation in steps:
        args = _args(tool_input)
        key = name + "\0" + json.dumps(args, sort_keys=True, default=str)
        if seen.get(key, 0):
            seen[key] -= 1  # the tool node already carries this call, with its own timing
            continue
        start, end = agent_window
        calls.append(ToolCall(name=name, arguments=args, result=observation, actor=agent_name, start_ns=start, end_ns=end))
    calls.sort(key=lambda c: (c.start_ns is None, c.start_ns or 0, c.name))
    ep.tool_calls.extend(calls)
    started = raw.get("startedAt")
    stopped = raw.get("stoppedAt")
    start_ns = _iso_to_ns(started, "startedAt") if isinstance(started, str) and started else None
    stop_ns = _iso_to_ns(stopped, "stoppedAt") if isinstance(stopped, str) and stopped else None
    if start_ns is None:
        stamped = [c.start_ns for c in calls if c.start_ns is not None]
        for name in run_data:
            for run in _runs_of(run_data, name):
                st, _en = _ms_window(run)
                if st is not None:
                    stamped.append(st)
        start_ns = min(stamped) if stamped else None
    ep.t0_ns = start_ns
    if start_ns is not None and stop_ns is not None and stop_ns >= start_ns:
        ep.duration_s = (stop_ns - start_ns) / 1e9
    if raw.get("id") not in (None, ""):
        ep.probe = str(raw["id"])
    elif not ep.probe:
        ep.probe = str(start_ns or "turn")


def _n8n(tr: list, ep: Episode, raw: dict) -> None:
    """n8n execution JSON: one execution is one turn.

    Turns that share ``sessionId`` (or, when that is absent, the Chat Trigger node's literal session key) are one
    conversation. ``chatInput`` wrapped as JSON, and message objects, become plain user text. Each tool-node run
    becomes a tool call with its arguments, result and ``startTime`` / ``executionTime``. The Simple Memory node is
    context only and is not a tool call.

    A legacy recording that is not an execution export still maps ``llm_route_raw`` onto an assistant message.
    Run-level tool definitions (``extra.tool_inputs_whole_run``) stay on ``final_state["run_tool_calls"]`` and are
    not per-turn spans: that export does not record which turn made which call.
    """
    result = _execution_result(raw)
    if result is not None:
        _n8n_execution(raw, result, ep)
        return
    for t in tr:
        if isinstance(t, dict) and "llm_route_raw" in t:
            ep.messages.append(Message("assistant", str(t["llm_route_raw"]), actor="router"))


def _n8n_run_calls(raw: dict) -> list[dict]:
    ex = raw.get("extra") or {}
    ins = ex.get("tool_inputs_whole_run") or []
    res = ex.get("tool_results_whole_run") or []
    return [{"name": (x.get("tool") or x.get("name") or "mcp_tool") if isinstance(x, dict) else "mcp_tool", "result": res[i]}
            for i, x in enumerate(ins) if i < len(res) and res[i] is not None]


def _is_error(d: dict) -> bool:
    """A tool event failed if it carries an ``error`` field or its result object does (``{"error": ...}``)."""
    if d.get("error"):
        return True
    res = d.get("result")
    if isinstance(res, str) and res[:1] == "{":
        try:
            res = json.loads(res)
        except ValueError:
            return False
    return isinstance(res, dict) and bool(res.get("error"))


def _events(tr: list, ep: Episode) -> None:
    for t in tr:
        k, name, d = t.get("kind"), t.get("name", ""), t.get("data")
        if isinstance(d, str):
            try:
                d = json.loads(d)
            except Exception:
                d = {"content": d}
        d = d or {}
        if k == "tool":
            a = d.get("args", {k2: v for k2, v in d.items() if k2 not in ("result", "reason", "error")})
            ep.tool_calls.append(ToolCall(name=name, arguments=_args(a), result=d.get("result"), error=_is_error(d)))
        elif k == "write":
            ep.tool_calls.append(ToolCall(name=name, arguments=_args(d)))
        elif k == "message":
            src = d.get("source", "")
            if name == "ToolCallRequestEvent":
                ep.tool_calls += _autogen_calls(str(d.get("content", "")), src)
            elif name == "HandoffMessage":
                ep.handoffs.append(Handoff(src, str(d.get("target", ""))))
            else:
                ep.messages.append(Message("user" if src == "user" else "assistant", str(d.get("content", "")), actor=src))
        elif k == "route" and d.get("next"):
            ep.handoffs.append(Handoff(name, str(d["next"])))


DIALECTS = {"steps": _steps, "openai_agents": _openai_agents, "langgraph_msgs": _langgraph_msgs, "autogen": _autogen, "events": _events}


def _text(v: Any) -> str:
    if v is None:
        return ""
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)


def _effects(raw: dict, paths: list[str], kind: str) -> list[StateChange]:
    out = []
    for p in paths:
        p, _, want = p.partition("==")
        v = get_path(raw, p)
        if want:
            v = str(v) == want
        if isinstance(v, list):
            out += [StateChange(kind, p.split(".")[-1], x) for x in v]
        elif isinstance(v, bool | str | int | float) and v and v is not False:
            out.append(StateChange(kind, p.split(".")[-1], v))
    return out


_PLUGINS: dict[str, Any] = {}


def _plugin(dialect: str, base):
    """Load ``to_trace(raw, ep)`` from a user mapping module (``--dialect file:my_mapping.py``), relative to ``base``."""
    import importlib.util
    from pathlib import Path

    f = Path(base or Path.cwd()) / dialect[5:]
    key = str(f.resolve())
    if key not in _PLUGINS:
        spec = importlib.util.spec_from_file_location(f"agentest_adapter_{f.stem}", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PLUGINS[key] = mod.to_trace
    return _PLUGINS[key]


CONVERSATION_KEYS = ("conversation_id", "session_id", "thread_id", "session", "thread")


def adapt(raw: dict, mapping: dict, is_write=None, base=None) -> Episode:
    """Convert one recorded native run into an :class:`Episode` using a pure-data ``mapping``
    (``dialect``, ``framework``, ``observations``: where facts live in the native record)."""
    obs = mapping.get("observations", {})
    dialect = mapping.get("dialect", "steps")
    ep = Episode(agent=raw.get("agent", ""), probe=raw.get("probe", ""), rep=int(raw.get("rep", 0)),
                 input=_text(raw.get("input")), error=raw.get("error"), framework=mapping.get("framework", ""))
    inp = raw.get("input")
    if isinstance(inp, dict):
        ep.conversation = str(next((inp[k] for k in CONVERSATION_KEYS if inp.get(k)), "") or "")
    tr = raw.get("trace") or []
    if dialect.startswith("file:"):
        _plugin(dialect, base)(raw, ep)
    elif dialect == "n8n":
        _n8n(tr, ep, raw)
    else:
        DIALECTS[dialect](tr, ep)
    if ep.input:
        ep.messages.insert(0, Message("user", ep.input))
    for c in ep.tool_calls:
        c.side_effect = "unknown" if is_write is None else ("write" if is_write(c.name) else "read")
    out = raw.get("output") or {}
    ep.final_state = {"output": out, "extra": raw.get("extra") or {}, "input": raw.get("input")}
    if dialect == "n8n":
        ep.final_state["run_tool_calls"] = _n8n_run_calls(raw)
    ep.events = list(tr) if isinstance(tr, list) else [tr]
    if raw.get("elapsed_s") is not None:  # a log that already measured the run wins; otherwise keep a duration the dialect read
        ep.duration_s = raw.get("elapsed_s")
    found = next((_text(get_path(raw, p)) for p in obs.get("final_answer", []) if get_path(raw, p) not in (None, "")), None)
    if found is not None:  # a mapping path wins; otherwise keep a final answer the dialect already read (n8n agent output)
        ep.final_answer = found
    ep.state_changes = _effects(raw, obs.get("executed", []), "executed") + _effects(raw, obs.get("pending", []), "pending") \
        + _effects(raw, obs.get("unapproved", []), "unapproved") + _effects(raw, obs.get("state_diff", []), "diff")
    if any(get_path(raw, p) for p in obs.get("approval_gate", [])):
        ep.approvals.append(Approval(action="human_gate", granted=True, approver="", policy_version=""))
    for p in obs.get("approvals", []):
        for a in get_path(raw, p) or []:
            if isinstance(a, dict):
                ep.approvals.append(Approval(action=str(a.get("action", "")), granted=bool(a.get("granted", a.get("approved", True))),
                                             approver=str(a.get("approver", "")), target=str(a.get("object", a.get("target", ""))),
                                             policy_version=str(a.get("policy_version", "")), reason=str(a.get("reason") or "")))
    return ep


STEP_KINDS = {"llm", "message", "subagent", "step"}


VERDICT_KEYS = ("critic", "guardrail", "verdict", "review", "review_decision", "policy_decision")
VERDICT_VALUES = {"pass": True, "approve": True, "approved": True, "allow": True, "ok": True, "accept": True, "accepted": True,
                  "fail": False, "reject": False, "rejected": False, "deny": False, "denied": False, "block": False,
                  "blocked": False, "tripped": False, "unsafe": False, "safe": True}


def _review_decisions(raw: dict, ep) -> None:
    """Review / guardrail verdicts logged as plain steps (critic PASS, guardrail TRIPPED, ...) are policy decisions:
    emit them as agentest.approval spans, carrying the logged policy version if there is one. Pure mapping."""
    if ep.approvals:
        return
    for t in raw.get("trace") or []:
        if not isinstance(t, dict):
            continue
        for k in VERDICT_KEYS:
            v = t.get(k)
            if isinstance(v, str) and v.strip().lower() in VERDICT_VALUES:
                ep.approvals.append(Approval(action=f"review:{k}", granted=VERDICT_VALUES[v.strip().lower()], approver=k,
                                             policy_version=str(t.get("policy_version") or t.get("policyVersion") or "")))


REASON_KEYS = ("reason", "reasons", "why", "rationale", "justification")  # common log spellings of a tool-call rationale


def _reason(*objs) -> str | None:
    for o in objs:
        for src in (o, o.get("args") if isinstance(o.get("args"), dict) else {}, o.get("input") if isinstance(o.get("input"), dict) else {}):
            for k in REASON_KEYS:
                v = src.get(k)
                if v:
                    return "; ".join(map(str, v)) if isinstance(v, list) else str(v)
    return None


def _native_extras(raw: dict, ep, obs: dict) -> tuple[list[dict], list[dict], list[str]]:
    """Log fields with an OTel home: tool reasons / source timestamps (span attrs), harness verdicts
    (``gen_ai.evaluation.result``), LLM steps (``chat`` spans). Pure mapping, no verdicts computed here."""
    tr = [t for t in (raw.get("trace") or []) if isinstance(t, dict)]
    tool_attrs: list[dict] = []
    steps: list[str] = []
    for t in tr:
        d = t.get("data")
        if isinstance(d, str):
            try:
                d = json.loads(d)
            except ValueError:
                d = {}
        d = d if isinstance(d, dict) else {}
        if t.get("kind") in ("tool", "write"):
            tool_attrs.append({"agentest.tool.reason": _reason(d, t),
                               "agentest.source.seq": t.get("seq"), "agentest.source.time_s": t.get("mono")})
        elif t.get("kind") in ("llm", "step", "subagent"):
            steps.append(str(d.get("content", ""))[:200] or t.get("kind"))
        elif "name" in t and "kind" not in t and any(k in t for k in REASON_KEYS):
            tool_attrs.append({"agentest.tool.reason": _reason(t)})
    if len(tool_attrs) != len(ep.tool_calls):
        tool_attrs = tool_attrs[: len(ep.tool_calls)] if tool_attrs else []
    evals = []
    for p in obs.get("evaluation", []):
        v = get_path(raw, p)
        if v is not None:
            evals.append({"gen_ai.evaluation.name": "harness_oracle", "gen_ai.evaluation.score.value": 1.0 if v else 0.0,
                          "gen_ai.evaluation.score.label": "pass" if v else "fail",
                          "gen_ai.evaluation.explanation": str((raw.get("extra") or {}).get("note", ""))[:200] or None})
    mono = [float(t["mono"]) for t in tr if isinstance(t.get("mono"), (int, float))]
    if mono and (ep.duration_s or 0) < max(mono):
        ep.duration_s = max(mono)
    return tool_attrs, evals, steps


def labels_attrs(labels: dict | None, input_id: str) -> dict:
    """Test-harness labels for one input -> root-span attributes (``agentest.input.*`` / ``agentest.test.*``)."""
    labels = labels or {}
    one = (labels.get("inputs") or {}).get(input_id, {})
    return {"agentest.input.families": list(one.get("families") or []) or None, "agentest.input.injected": list(one.get("injected") or []) or None,
            "agentest.test.canaries": list(labels.get("canaries") or []) or None,
            "agentest.input.relations": json.dumps(labels["relations"]) if labels.get("relations") else None}


def to_docs(raws: list[dict], mapping: dict, service: str, is_write=None, base=None) -> list[dict]:
    """Native records -> OTLP/JSON documents (one trace each)."""
    from agentest.standards.otel import to_otlp

    obs = mapping.get("observations", {})
    docs = []
    for raw in raws:
        ep = adapt(raw, mapping, is_write, base)
        extra = {}
        for k in ("citations", "outputs"):
            vals = [get_path(ep.final_state, p) for p in obs.get(k, [])]
            if obs.get(k):
                extra[f"agentest.{k}"] = [v for v in vals if v]
        _review_decisions(raw, ep)
        extra.update({k: v for k, v in labels_attrs(mapping.get("labels"), ep.probe).items() if v is not None})
        docs.append(to_otlp(ep, service, extra, *_native_extras(raw, ep, obs)))
    return docs


def read_native(path) -> list[dict]:
    """One native log file: a JSON array of records, one JSON object, or JSONL (one object per line)."""
    from pathlib import Path

    text = Path(path).read_text()
    try:
        if str(path).endswith(".jsonl"):
            rows = []
            for i, ln in enumerate(text.splitlines(), 1):
                if not ln.strip():
                    continue
                try:
                    rec = json.loads(ln)
                except json.JSONDecodeError as e:
                    raise ValueError(f"native log is malformed JSON on line {i}: {e.msg}") from e
                if not isinstance(rec, dict):
                    raise ValueError(f"native log is malformed: line {i} is not an object")
                rows.append(rec)
            return rows
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"native log is malformed JSON: {e.msg}") from e
    if isinstance(doc, dict):
        return [doc]
    if isinstance(doc, list) and all(isinstance(r, dict) for r in doc):
        return doc
    raise ValueError("native log is malformed: expected a JSON object or an array of objects")
