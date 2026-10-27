"""Import native agent logs into OTLP/JSON (OpenTelemetry GenAI spans): ``agentest std import``.

This is the only framework-specific code, and it is pure mapping, driven by data: a *dialect* (how a framework
writes its log) and a *mapping* file (where the facts sit in a native record). It computes no verdicts. Agents that
emit OpenTelemetry GenAI spans themselves need none of this.

Dialects:
  steps            plain Python / LangGraph node logs / LlamaIndex steps / CrewAI task list
  openai_agents    OpenAI Agents SDK RunItems (tool_call_item, handoff_output_item, ...)
  langgraph_msgs   LangGraph message list (role, content, tool_calls)
  autogen          AutoGen AgentChat events (ToolCallRequestEvent / FunctionCall reprs)
  n8n              n8n execution data
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


def _n8n(tr: list, ep: Episode, raw: dict) -> None:
    """n8n: per-episode tool calls are NOT recoverable from the export.

    ``tool_inputs_whole_run`` lists the tool *definitions* the AI Agent node was offered
    (name + description, no arguments) and ``tool_results_whole_run`` the results of the
    whole recording run; both are identical across episodes. So no per-episode tool calls
    are recorded; the run-level calls actually made (a definition paired with a result)
    go to ``final_state["run_tool_calls"]`` for checks that want run-level evidence.
    """
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
    ep.duration_s = raw.get("elapsed_s")
    ep.final_answer = next((_text(get_path(raw, p)) for p in obs.get("final_answer", []) if get_path(raw, p) not in (None, "")), "")
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
    from pathlib import Path

    text = Path(path).read_text()
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()] if str(path).endswith(".jsonl") else json.loads(text)
