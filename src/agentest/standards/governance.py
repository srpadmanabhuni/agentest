"""Governance-extension converters and the MCP tool-annotation hint fallback (v3.5).

The extension ``urn:agentest:a2a-ext:governance:v1`` (spec: ``docs/rfc/0001-governance-extension.md``) is plain
data. Most agent frameworks already hold some of those facts in their own configuration. These converters read
them and return extension ``params``. They need **no framework import**: they read plain dicts (an exported or
hand-written config) or live framework objects by attribute name (duck typing), so the frameworks stay optional and
unpinned.

=============  =====================================================================================================
source         facts read -> governance params
=============  =====================================================================================================
MCP tools      ``annotations.readOnlyHint/destructiveHint`` -> ``approval.required`` (destructive writes);
               ``annotations.rateLimit`` / ``_meta.rateLimit`` -> ``rateLimits``; any tool -> ``capabilities.tools``
LangGraph      ``interrupt_before`` / ``interrupt_after`` on a tool node -> ``approval.required`` (that node's tools);
               ``recursion_limit`` -> ``limits.max_steps``; > 1 agent node -> ``capabilities.multi_agent``,
               ``roles.actors``; supervisor -> ``roles.orchestrators``
AutoGen        ``human_input_mode: ALWAYS`` on the agent that executes tools -> ``approval.required``;
               ``max_consecutive_auto_reply`` / ``max_turns`` -> ``limits.max_steps``; group chat manager / selector
               -> ``roles.orchestrators``; per-agent tools -> ``roles.actors``
CrewAI         task ``human_input: true`` -> ``approval.required`` (the task's tools, else its agent's tools);
               ``max_iter`` -> ``limits.max_steps``; ``max_rpm`` -> ``rateLimits`` (per tool of that agent, per 60 s);
               ``process: hierarchical`` / ``manager_agent`` -> ``roles.orchestrators``; ``roles.actors``
=============  =====================================================================================================

Every converter returns ``(params, provenance)``: provenance maps each produced field to the source fact, so a
reviewer can see why a fact was derived. Derived params never override published ones (:func:`merge`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentest.standards import GOV_EXT

MCP_DEFAULTS = {"readOnlyHint": False, "destructiveHint": True}


def _get(o: Any, key: str, default: Any = None) -> Any:
    """Field of a dict or attribute of an object (duck typing; no framework import)."""
    if isinstance(o, dict):
        return o.get(key, default)
    return getattr(o, key, default)


def _name(t: Any) -> str:
    """A tool's name: a string, ``name``, an OpenAI-style ``{"function": {"name"}}`` or a callable's ``__name__``."""
    if isinstance(t, str):
        return t
    fn = _get(t, "function")
    n = _get(t, "name") or (fn.get("name") if isinstance(fn, dict) else None) or _get(t, "__name__")
    return str(n or "")


def _tool_names(ts: Any) -> list[str]:
    if ts is None:
        return []
    if isinstance(ts, dict) and "tools" not in ts:  # name -> callable (AutoGen function_map, LangGraph tools_by_name)
        return sorted(str(k) for k in ts)
    if isinstance(ts, dict):
        ts = ts["tools"]
    return [n for n in (_name(t) for t in ts) if n]


def _set(params: dict, prov: dict, path: str, value: Any, why: str) -> None:
    cur = params
    keys = path.split(".")
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value
    prov[path] = why


def _finish(params: dict, prov: dict) -> tuple[dict, dict]:
    if "approval" in params:
        params["approval"]["required"] = sorted(set(params["approval"]["required"]))
    return params, prov


# ---------------------------------------------------------------- MCP tool-annotation hints

def from_mcp(tools: Any) -> tuple[dict, dict]:
    """MCP ``tools/list`` (``{"tools": [...]}`` or a list) -> params. Destructive writes (readOnlyHint false and
    destructiveHint true, MCP defaults applied) need approval; that is the same fallback the rules use when no
    ``approval`` is published."""
    ts = tools.get("tools", []) if isinstance(tools, dict) else list(tools or [])
    params, prov = {}, {}
    if not ts:
        return params, prov
    _set(params, prov, "capabilities.tools", True, "MCP tools/list is not empty")
    gated, rl = [], {}
    for t in ts:
        ann = {**MCP_DEFAULTS, **(_get(t, "annotations") or {})}
        if not ann["readOnlyHint"] and ann["destructiveHint"]:
            gated.append(_name(t))
        for holder in (_get(t, "annotations") or {}, _get(t, "_meta") or {}):
            if isinstance(holder.get("rateLimit"), dict):
                rl.setdefault(_name(t), dict(holder["rateLimit"]))
    _set(params, prov, "approval.required", gated, "MCP annotations: readOnlyHint=false and destructiveHint=true (MCP defaults applied)")
    if rl:
        _set(params, prov, "rateLimits", rl, "MCP annotations.rateLimit / _meta.rateLimit")
    return _finish(params, prov)


# ---------------------------------------------------------------- LangGraph

def from_langgraph(graph: Any, config: dict | None = None) -> tuple[dict, dict]:
    """A LangGraph graph or its exported description. Reads ``nodes`` (name -> node; a tool node exposes
    ``tools_by_name`` / ``tools``; an agent node may carry ``tools`` and ``agent: true``), ``interrupt_before`` /
    ``interrupt_after`` (node names, or "*"), ``supervisor`` and ``config.recursion_limit``."""
    params, prov = {}, {}
    nodes = _get(graph, "nodes") or {}
    if isinstance(nodes, list):
        nodes = {_get(n, "name") or _get(n, "id"): n for n in nodes}
    node_tools = {}
    for name, n in nodes.items():
        data = _get(n, "data", n)
        ts = _get(data, "tools_by_name") or _get(data, "tools")
        if ts:
            node_tools[str(name)] = _tool_names(ts)
    all_tools = sorted({t for ts in node_tools.values() for t in ts})
    if all_tools:
        _set(params, prov, "capabilities.tools", True, "graph has tool nodes")
    gated = []
    for key in ("interrupt_before", "interrupt_after"):
        for n in _get(graph, key) or []:
            hit = all_tools if n == "*" else node_tools.get(str(n), [])
            gated += hit
            if hit:
                prov.setdefault("approval.required", f"{key} on tool node(s)")
    if gated:
        _set(params, prov, "approval.required", gated, prov.get("approval.required", "interrupt on tool node"))
        _set(params, prov, "capabilities.approval", True, "graph interrupts before/after tool execution")
    lim = (config or {}).get("recursion_limit", _get(graph, "recursion_limit"))
    if isinstance(lim, (int, float)) and lim > 0:
        _set(params, prov, "limits.max_steps", int(lim), "LangGraph recursion_limit")
    agents = {str(k): node_tools.get(str(k), []) for k, n in nodes.items() if _get(_get(n, "data", n), "agent")}
    if len(agents) > 1:
        _set(params, prov, "capabilities.multi_agent", True, "more than one agent node")
        _set(params, prov, "roles.actors", {k: sorted(v) for k, v in agents.items()}, "agent nodes and their tools")
    sup = _get(graph, "supervisor")
    if sup:
        _set(params, prov, "roles.orchestrators", [str(sup)], "LangGraph supervisor node")
    return _finish(params, prov)


# ---------------------------------------------------------------- AutoGen

def _agent_tools(a: Any) -> list[str]:
    ts = _tool_names(_get(a, "tools")) or _tool_names(_get(a, "function_map"))
    llm = _get(a, "llm_config") or {}
    if not ts and isinstance(llm, dict):
        ts = _tool_names(llm.get("tools") or llm.get("functions"))
    return ts


def from_autogen(team: Any) -> tuple[dict, dict]:
    """AutoGen 0.2 (``ConversableAgent`` / ``UserProxyAgent`` / ``GroupChatManager``) or AgentChat 0.4
    (``AssistantAgent``, teams with ``participants`` and ``max_turns``), as objects or an exported dict with
    ``agents`` or ``participants``."""
    params, prov = {}, {}
    agents = _get(team, "agents") or _get(team, "participants") or ([team] if _get(team, "name") else [])
    tools_by_agent = {str(_get(a, "name")): _agent_tools(a) for a in agents}
    if any(tools_by_agent.values()):
        _set(params, prov, "capabilities.tools", True, "agents declare tools / function_map")
    gated = [t for a in agents if str(_get(a, "human_input_mode") or "").upper() == "ALWAYS" for t in tools_by_agent[str(_get(a, "name"))]]
    if gated:
        _set(params, prov, "approval.required", gated, "human_input_mode=ALWAYS on the tool-executing agent")
        _set(params, prov, "capabilities.approval", True, "a human is asked before tool execution")
    caps = [x for x in [_get(team, "max_turns"), _get(team, "max_round")] + [_get(a, "max_consecutive_auto_reply") for a in agents]
            if isinstance(x, int) and not isinstance(x, bool) and x > 0]
    if caps:
        _set(params, prov, "limits.max_steps", max(caps), "max_turns / max_round / max_consecutive_auto_reply")
    if len(agents) > 1:
        _set(params, prov, "capabilities.multi_agent", True, "more than one participant")
        _set(params, prov, "roles.actors", {k: sorted(v) for k, v in tools_by_agent.items() if v}, "participants and their tools")
    mgr = _get(team, "manager") or _get(team, "selector")
    if mgr is not None:
        _set(params, prov, "roles.orchestrators", [str(_get(mgr, "name") or mgr)], "group chat manager / selector")
    return _finish(params, prov)


# ---------------------------------------------------------------- CrewAI

def from_crewai(crew: Any) -> tuple[dict, dict]:
    """A CrewAI ``Crew`` (or its YAML/JSON export): ``agents`` (role, tools, max_iter, max_rpm, allow_delegation),
    ``tasks`` (agent, tools, human_input) and ``process`` / ``manager_agent``."""
    params, prov = {}, {}
    agents = _get(crew, "agents") or []
    if isinstance(agents, dict):  # crewai agents.yaml: role key -> config
        agents = [{"role": k, **(v or {})} for k, v in agents.items()]
    tasks = _get(crew, "tasks") or []
    if isinstance(tasks, dict):
        tasks = [{"name": k, **(v or {})} for k, v in tasks.items()]
    role = lambda a: str(_get(a, "role") or _get(a, "name") or "")  # noqa: E731
    tools = {role(a): _tool_names(_get(a, "tools")) for a in agents}
    if any(tools.values()) or any(_tool_names(_get(t, "tools")) for t in tasks):
        _set(params, prov, "capabilities.tools", True, "agents or tasks declare tools")
    gated = []
    for t in tasks:
        if _get(t, "human_input"):
            ag = _get(t, "agent")
            gated += _tool_names(_get(t, "tools")) or tools.get(role(ag) if ag is not None and not isinstance(ag, str) else str(ag or ""), [])
    if gated:
        _set(params, prov, "approval.required", gated, "task human_input=true (the task's tools, else its agent's)")
        _set(params, prov, "capabilities.approval", True, "a task asks a human before it completes")
    iters = [x for x in (_get(a, "max_iter") for a in agents) if isinstance(x, int) and x > 0]
    if iters:
        _set(params, prov, "limits.max_steps", max(iters), "agent max_iter")
    rl = {}
    for a in agents:
        rpm = _get(a, "max_rpm")
        if isinstance(rpm, int) and rpm > 0:
            for tn in tools.get(role(a), []):
                rl.setdefault(tn, {"maxCalls": rpm, "perSeconds": 60})
    if rl:
        _set(params, prov, "rateLimits", rl, "agent max_rpm, applied per tool of that agent (conservative: max_rpm bounds all calls)")
    if len(agents) > 1:
        _set(params, prov, "capabilities.multi_agent", True, "more than one agent")
        _set(params, prov, "roles.actors", {k: sorted(v) for k, v in tools.items() if v}, "agent roles and their tools")
    mgr = _get(crew, "manager_agent")
    if mgr is not None or str(_get(crew, "process") or "").lower().endswith("hierarchical"):
        _set(params, prov, "roles.orchestrators", [role(mgr) if mgr is not None and not isinstance(mgr, str) else str(mgr or "manager")],
             "hierarchical process / manager_agent")
    return _finish(params, prov)


CONVERTERS = {"mcp": from_mcp, "langgraph": from_langgraph, "autogen": from_autogen, "crewai": from_crewai}


def merge(published: dict | None, *derived: dict) -> dict:
    """Published params win key by key (recursively for objects); derived ones only fill gaps."""
    out = json.loads(json.dumps(published or {}))
    for d in derived:
        for k, v in (d or {}).items():
            if k not in out:
                out[k] = json.loads(json.dumps(v))
            elif isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = merge(out[k], v)
    return out


def extension(params: dict) -> dict:
    """The AgentCard ``capabilities.extensions[]`` entry."""
    return {"uri": GOV_EXT, "description": "agentest governance facts (policy as data)", "required": False, "params": params}


def mcp_fallback_enabled() -> bool:
    """MCP-hint fallback for agents that publish no governance extension: config ``governance_fallback: mcp`` or
    ``AGENTEST_GOVERNANCE_FALLBACK=mcp``. Off by default (verdicts stay as published)."""
    import os

    from agentest.standards import ext

    return (ext.CONFIG.get("governance_fallback") or os.environ.get("AGENTEST_GOVERNANCE_FALLBACK") or "").lower() == "mcp"


def load_source(path: str | Path) -> Any:
    text = Path(path).read_text(encoding="utf-8")
    if str(path).endswith((".yaml", ".yml")):
        import yaml

        return yaml.safe_load(text)
    return json.loads(text)
