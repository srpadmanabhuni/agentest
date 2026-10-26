"""Adapters: framework-native recorded episodes -> standard :class:`~agentest.model.trace.Episode`.

The adapter is the only framework-specific code. It extracts messages, tool
calls and handoffs from the native trace; the *profile* (not the adapter) says
which tools write and where executed / pending effects and approvals live.

Dialects (named in each profile's ``adapter:`` key):
  steps            plain Python / LangGraph node logs / LlamaIndex steps / CrewAI task list
  openai_agents    OpenAI Agents SDK RunItems (tool_call_item, handoff_output_item, ...)
  langgraph_msgs   LangGraph message list (role, content, tool_calls)
  autogen          AutoGen AgentChat events (ToolCallRequestEvent / FunctionCall reprs)
  n8n              n8n execution data (tool_inputs_whole_run / tool_results_whole_run)
  events           seq/kind event log used by reference agents a13-a25 (llm/tool/write/message/mcp)
  sample           in-process sample agents (agentest.types.Trace + Env snapshot)
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from agentest.model.profile import Profile, get_path
from agentest.model.trace import Approval, Episode, Handoff, Message, StateChange, ToolCall

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
        if name == "retrieve":
            ep.tool_calls.append(ToolCall(name="retrieve", arguments={}, result=t.get("sources")))
        elif t.get("agent") and "output" in t:  # CrewAI task output
            ep.messages.append(Message("assistant", str(t["output"]), actor=t["agent"]))
        for n in t.get("log", []) or []:  # LangGraph durable node log (a12)
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
            a = d.get("args", {k2: v for k2, v in d.items() if k2 not in ("result", "reason")})
            ep.tool_calls.append(ToolCall(name=name, arguments=_args(a), result=d.get("result")))
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


def _plugin(prof: Profile):
    """Load ``to_trace(raw, ep)`` from an adapter file named in the profile (``adapter: file:x.py``)."""
    import importlib.util
    from pathlib import Path

    f = (Path(prof.source).parent if prof.source else Path.cwd()) / prof.adapter[5:]
    key = str(f.resolve())
    if key not in _PLUGINS:
        spec = importlib.util.spec_from_file_location(f"agentest_adapter_{f.stem}", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PLUGINS[key] = mod.to_trace
    return _PLUGINS[key]


def adapt(raw: dict, prof: Profile) -> Episode:
    """Convert one recorded native episode into the standard trace using the profile."""
    obs = prof.observations
    ep = Episode(agent=raw.get("agent", prof.agent), probe=raw.get("probe", ""), rep=int(raw.get("rep", 0)),
                 input=_text(raw.get("input")), error=raw.get("error"), framework=prof.framework)
    tr = raw.get("trace") or []
    if prof.adapter.startswith("file:"):
        _plugin(prof)(raw, ep)
    elif prof.adapter == "n8n":
        _n8n(tr, ep, raw)
    else:
        DIALECTS[prof.adapter](tr, ep)
    if ep.input:
        ep.messages.insert(0, Message("user", ep.input))
    for c in ep.tool_calls:
        c.side_effect = prof.side_effect(c.name)
    out = raw.get("output") or {}
    ep.final_state = {"output": out, "extra": raw.get("extra") or {}, "input": raw.get("input")}
    if prof.adapter == "n8n":
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
                                             policy_version=str(a.get("policy_version", ""))))
    return ep


# ---- sample agents (in-process; recorded on the fly) --------------------------------------------

def record_sample(agent: str, ids: list[str]) -> list[dict]:
    """Run sample ``agent`` through the scenario of each ID and record a native episode dict.

    Captures the agent's :class:`agentest.types.Trace`, the env snapshot before/after
    and the approval tokens, by wrapping ``SampleAgent.handle``. Multi-run IDs are skipped.
    """
    import agentest.samples as S
    from agentest.cases import multi_run
    from agentest.cases.registry import CASE_REGISTRY

    rec: list[dict] = []
    real = S.get_sample(agent)

    class Spy:
        def handle(self, cid, env):
            before = env.snapshot()
            tr = real.handle(cid, env)
            after = env.snapshot()
            changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
            rec.append({"agent": agent, "probe": cid, "rep": 0, "input": cid,
                        "trace": [{"name": c.name, "args": c.args, "result": c.result, "allowed": c.allowed, "ok": c.succeeded,
                                   "actor": (c.meta or {}).get("actor", "")} for c in tr.calls],
                        "output": {"message": tr.message, "claims_success": tr.claims_success, "changed": changed,
                                   "emails": list(env.emails), "outputs": (env.extras or {}).get("outputs"), "approvals": [{"action": t.tool, "object": t.target, "approver": t.granted_by,
                                                                              "granted": True} for t in env.approvals.tokens.values()],
                                   "authz": [{"action": x.task or x.resource, "object": x.resource, "approver": x.actor, "granted": x.decision == "allow",
                                              "policy_version": x.policy_version} for x in env.authz_log.entries],
                                   "env": snap(env), "tr": snap(tr)},
                        "extra": {}})
            return tr

    orig = S.get_sample
    from agentest.samples.record import snap
    S.get_sample = lambda name: Spy() if name == agent else orig(name)
    try:
        for i in ids:
            if i in CASE_REGISTRY and i not in multi_run.MULTI_RUN_IDS:
                try:
                    CASE_REGISTRY[i].run(agent)
                except Exception as ex:  # record the failure honestly
                    rec.append({"agent": agent, "probe": i, "rep": 0, "input": i, "trace": [], "output": {}, "extra": {}, "error": repr(ex)[:200]})
    finally:
        S.get_sample = orig
    from agentest.config.thresholds import T1_002_K, T1_003_K
    from agentest.samples import worlds
    from agentest.samples.record import snap as _snap

    for i in ids:
        if i in multi_run.MULTI_RUN_IDS:
            once = multi_run._once_fn(i, agent)
            for r in range({"T1-002": T1_002_K, "T1-003": T1_003_K}[i]):
                env = multi_run._fresh_high_risk_env()
                tr = once(env)
                rec.append({"agent": agent, "probe": i, "rep": r, "input": i, "trace": [],
                            "output": {"env": _snap(env), "tr": _snap(tr)}, "extra": {}})
        elif i in worlds.SCEN:
            rec.append(worlds.record(i, agent))
    return rec


def _sample(tr: list, ep: Episode) -> None:
    for t in tr:
        ep.tool_calls.append(ToolCall(name=t["name"], arguments=_args(t.get("args")), result=t.get("result"), actor=t.get("actor", ""),
                                      error=not t.get("ok", True)))


DIALECTS["sample"] = _sample
