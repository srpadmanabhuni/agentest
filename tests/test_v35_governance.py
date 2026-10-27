"""v3.5 (3): governance converters (LangGraph, AutoGen, CrewAI, MCP hints) and the opt-in MCP-hint fallback."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace as NS

import jsonschema
import pytest

from agentest.standards import GOV_EXT, governance, metadata

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "src/agentest/standards/schemas/governance-extension.schema.json").read_text())
VALID = jsonschema.Draft202012Validator(SCHEMA)

MCP = {"tools": [
    {"name": "lookup_order", "annotations": {"readOnlyHint": True}},
    {"name": "request_refund", "annotations": {"readOnlyHint": False, "destructiveHint": True}, "_meta": {"rateLimit": {"maxCalls": 2, "perSeconds": 60}}},
    {"name": "add_note", "annotations": {"readOnlyHint": False, "destructiveHint": False}},
    {"name": "undeclared_tool"},  # MCP defaults: a destructive write
]}


def _ok(params):
    VALID.validate(params)
    return params


# ------------------------------------------------------------------ MCP hints

def test_mcp_hints_gate_destructive_writes_only():
    p, prov = governance.from_mcp(MCP)
    _ok(p)
    assert p["approval"]["required"] == ["request_refund", "undeclared_tool"]
    assert p["rateLimits"] == {"request_refund": {"maxCalls": 2, "perSeconds": 60}}
    assert p["capabilities"] == {"tools": True}
    assert "MCP" in prov["approval.required"]


def test_mcp_hints_negative_read_only_and_empty():
    p, _ = governance.from_mcp({"tools": [{"name": "a", "annotations": {"readOnlyHint": True}}, {"name": "b", "annotations": {"destructiveHint": False}}]})
    assert _ok(p)["approval"]["required"] == []
    assert governance.from_mcp({"tools": []}) == ({}, {})
    assert governance.from_mcp([]) == ({}, {})


# ------------------------------------------------------------------ LangGraph

def _tool(name):
    def f():
        return None
    f.__name__ = name
    return f


def test_langgraph_object_interrupt_before_tool_node():
    g = NS(nodes={"agent": NS(data=NS(tools=None)), "tools": NS(data=NS(tools_by_name={"refund": _tool("refund"), "lookup": _tool("lookup")}))},
           interrupt_before=["tools"], interrupt_after=[])
    p, prov = governance.from_langgraph(g, {"recursion_limit": 25})
    _ok(p)
    assert p["approval"]["required"] == ["lookup", "refund"]
    assert p["limits"]["max_steps"] == 25 and p["capabilities"]["approval"] is True
    assert "interrupt_before" in prov["approval.required"]


def test_langgraph_dict_supervisor_multi_agent_and_wildcard():
    g = {"nodes": [{"name": "billing", "agent": True, "tools": [{"name": "refund"}]},
                   {"name": "support", "agent": True, "tools": ["lookup"]}],
         "interrupt_after": ["*"], "supervisor": "router"}
    p, _ = governance.from_langgraph(g)
    _ok(p)
    assert p["approval"]["required"] == ["lookup", "refund"]
    assert p["roles"] == {"actors": {"billing": ["refund"], "support": ["lookup"]}, "orchestrators": ["router"]}
    assert p["capabilities"]["multi_agent"] is True


def test_langgraph_negative_no_interrupt_no_approval():
    p, _ = governance.from_langgraph({"nodes": {"tools": {"tools": ["refund"]}}, "interrupt_before": ["agent"]})
    assert "approval" not in _ok(p)
    assert governance.from_langgraph({}) == ({}, {})


# ------------------------------------------------------------------ AutoGen

def test_autogen_02_user_proxy_always_gates_its_functions():
    team = NS(agents=[NS(name="assistant", human_input_mode="NEVER", function_map=None, tools=None,
                         llm_config={"tools": [{"type": "function", "function": {"name": "refund"}}]}, max_consecutive_auto_reply=10),
                      NS(name="executor", human_input_mode="ALWAYS", function_map={"refund": _tool("refund")}, tools=None, llm_config=False,
                         max_consecutive_auto_reply=None)],
              manager=NS(name="chat_manager"), max_round=12)
    p, _ = governance.from_autogen(team)
    _ok(p)
    assert p["approval"]["required"] == ["refund"]
    assert p["limits"]["max_steps"] == 12
    assert p["roles"]["orchestrators"] == ["chat_manager"]
    assert p["roles"]["actors"] == {"assistant": ["refund"], "executor": ["refund"]}


def test_autogen_04_dict_team_negative_never():
    team = {"participants": [{"name": "a", "tools": ["lookup", "refund"], "human_input_mode": "NEVER"}, {"name": "b", "tools": []}], "max_turns": 5}
    p, _ = governance.from_autogen(team)
    _ok(p)
    assert "approval" not in p and p["limits"]["max_steps"] == 5
    assert p["roles"]["actors"] == {"a": ["lookup", "refund"]}
    # booleans are not turn limits
    assert "limits" not in governance.from_autogen({"agents": [{"name": "x", "max_consecutive_auto_reply": True}]})[0]


# ------------------------------------------------------------------ CrewAI

def test_crewai_human_input_task_and_rpm():
    crew = {"agents": [{"role": "Billing agent", "tools": [{"name": "refund"}], "max_iter": 15, "max_rpm": 10},
                       {"role": "Support agent", "tools": ["lookup"], "max_iter": 20}],
            "tasks": [{"description": "issue refund", "agent": "Billing agent", "human_input": True},
                      {"description": "look up", "agent": "Support agent", "human_input": False}],
            "process": "hierarchical"}
    p, prov = governance.from_crewai(crew)
    _ok(p)
    assert p["approval"]["required"] == ["refund"]
    assert p["limits"]["max_steps"] == 20
    assert p["rateLimits"] == {"refund": {"maxCalls": 10, "perSeconds": 60}}
    assert p["roles"]["orchestrators"] == ["manager"]
    assert "max_rpm" in prov["rateLimits"]


def test_crewai_objects_task_tools_win_and_yaml_style_agents():
    billing = NS(role="Billing", tools=[_tool("refund"), _tool("lookup")], max_iter=None, max_rpm=None)
    crew = NS(agents=[billing], tasks=[NS(agent=billing, tools=[_tool("refund")], human_input=True)], process="sequential", manager_agent=None)
    p, _ = governance.from_crewai(crew)
    assert _ok(p)["approval"]["required"] == ["refund"]  # only the task's own tools, not every tool of the agent
    assert "roles" not in p or "orchestrators" not in p.get("roles", {})
    p2, _ = governance.from_crewai({"agents": {"researcher": {"tools": ["search"]}}, "tasks": {"t": {"agent": "researcher"}}})
    assert "approval" not in _ok(p2) and p2["capabilities"]["tools"] is True


# ------------------------------------------------------------------ merge, extension, fallback, CLI

def test_merge_published_wins_and_fills_gaps():
    pub = {"approval": {"required": ["x"], "hostGated": True}, "languages": ["en"]}
    m = governance.merge(pub, {"approval": {"required": ["y"], "ttlSeconds": 60}, "limits": {"max_steps": 3}})
    assert m == {"approval": {"required": ["x"], "hostGated": True, "ttlSeconds": 60}, "languages": ["en"], "limits": {"max_steps": 3}}
    assert pub == {"approval": {"required": ["x"], "hostGated": True}, "languages": ["en"]}  # not mutated
    e = governance.extension({"languages": ["en"]})
    assert e["uri"] == GOV_EXT and e["required"] is False


def _agent_dir(tmp_path, card_ext=None):
    d = tmp_path / "agent-x"
    d.mkdir()
    (d / "tools.json").write_text(json.dumps(MCP))
    card = {"name": "x", "skills": [], "capabilities": {"extensions": [card_ext] if card_ext else []}}
    (d / "agent-card.json").write_text(json.dumps(card))
    return d


def test_fallback_off_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTEST_GOVERNANCE_FALLBACK", raising=False)
    assert metadata.load(_agent_dir(tmp_path)).gov == {}


def test_fallback_on_derives_from_mcp_but_never_overrides_a_published_extension(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTEST_GOVERNANCE_FALLBACK", "mcp")
    a = metadata.load(_agent_dir(tmp_path))
    assert a.g("approval", "required") == ["request_refund", "undeclared_tool"]
    (tmp_path / "b").mkdir()
    b = metadata.load(_agent_dir(tmp_path / "b", governance.extension({"languages": ["en"]})))
    assert b.gov == {"languages": ["en"]}


def test_cli_governance_writes_valid_card(tmp_path, capsys):
    from agentest.cli import main

    src = tmp_path / "crew.json"
    src.write_text(json.dumps({"agents": [{"role": "A", "tools": ["refund"]}], "tasks": [{"agent": "A", "human_input": True}]}))
    card = tmp_path / "card.json"
    card.write_text(json.dumps({"name": "x", "capabilities": {"extensions": [governance.extension({"approval": {"required": ["keep"]}})]}}))
    out = tmp_path / "out.json"
    assert main(["std", "governance", "--from", "crewai", str(src), "--card", str(card), "--out", str(out)]) == 0
    params = next(e["params"] for e in json.loads(out.read_text())["capabilities"]["extensions"] if e["uri"] == GOV_EXT)
    assert _ok(params)["approval"]["required"] == ["keep"]  # published wins
    assert params["capabilities"]["approval"] is True  # gaps filled
    assert "derived approval.required" in capsys.readouterr().err
    tools = tmp_path / "tools.json"
    tools.write_text(json.dumps(MCP))
    assert main(["std", "governance", "--from", "mcp", str(tools)]) == 0
    assert _ok(json.loads(capsys.readouterr().out)["params"])["approval"]["required"] == ["request_refund", "undeclared_tool"]
    assert main(["std", "governance"]) == 2


@pytest.mark.parametrize("mod", ["governance.py"])
def test_converters_import_no_framework(mod):
    tree = ast.parse((ROOT / "src/agentest/standards" / mod).read_text())
    names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not names & {"langgraph", "langchain", "langchain_core", "autogen", "autogen_agentchat", "crewai", "mcp"}
