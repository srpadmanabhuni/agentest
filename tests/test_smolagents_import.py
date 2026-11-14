"""smolagents dialect: memory steps import to the same verdicts as the equivalent LangGraph message log."""
import json
from pathlib import Path

from agentest.cli import main
from agentest.standards.importers import adapt

ROOT = Path(__file__).resolve().parents[1]
LG = ROOT / "examples" / "langgraph_import"
SM = ROOT / "examples" / "smolagents_import"
CARD, TOOLS = LG / "agents" / "expense_bot" / "agent-card.json", LG / "agents" / "expense_bot" / "tools.json"


def _verdicts(trace: Path, out: Path) -> dict:
    assert main(["std", "run", "--otlp", str(trace), "--card", str(CARD), "--tools", str(TOOLS), "--format", "json", "--out", str(out)]) in (0, 1)
    return {r["id"]: r["status"] for r in json.loads(out.read_text())["results"]}


def test_smolagents_example_matches_langgraph_verdicts(tmp_path):
    t = tmp_path / "s.otlp.jsonl"
    assert main(["std", "import", str(SM / "native" / "expense_bot.jsonl"), "--map", str(SM / "import" / "map.json"),
                 "--tools", str(TOOLS), "--service", "expense_bot", "--out", str(t)]) == 0
    got = _verdicts(t, tmp_path / "s.json")
    want = _verdicts(LG / "agents" / "expense_bot" / "traces" / "expense_bot.otlp.jsonl", tmp_path / "l.json")
    assert len(got) == 130 and got == want
    assert any(v == "fail" for v in got.values())  # the social-engineering episode is still caught


def _ep(steps, inp="do it"):
    return adapt({"agent": "a", "input": inp, "trace": steps}, {"dialect": "smolagents"})


def test_tool_calls_results_errors_and_final_answer():
    ep = _ep([
        {"task": "do it"},
        {"plan": "1. look up 2. write"},
        {"step_number": 1, "model_output": "Thought: look up first", "observations": "row 7",
         "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "lookup", "arguments": '{"q": "x"}'}}]},
        {"step_number": 2, "observations": None, "error": {"type": "AgentToolExecutionError", "message": "boom"},
         "tool_calls": [{"id": "c2", "type": "function", "function": {"name": "write", "arguments": {"k": 1}}}]},
        {"step_number": 3, "is_final_answer": True, "action_output": "done",
         "tool_calls": [{"id": "c3", "type": "function", "function": {"name": "final_answer", "arguments": {"answer": "done"}}}]},
    ])
    assert [(c.name, c.arguments, c.call_id, c.result, c.error) for c in ep.tool_calls] == [
        ("lookup", {"q": "x"}, "c1", "row 7", False), ("write", {"k": 1}, "c2", None, True)]
    assert [(m.role, m.content) for m in ep.messages] == [("user", "do it"), ("assistant", "done")]  # thoughts and plans skipped


def test_code_agent_and_final_answer_step():
    ep = _ep([{"task": "follow-up question"},
              {"step_number": 1, "code_action": "x = search('a')", "observations": "Execution logs: ok",
               "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "python_interpreter", "arguments": "x = search('a')"}}]},
              {"output": {"total": 3}}])
    assert [c.name for c in ep.tool_calls] == ["python_interpreter"] and ep.tool_calls[0].arguments == {"raw": "x = search('a')"}
    assert [(m.role, m.content) for m in ep.messages] == [("user", "do it"), ("user", "follow-up question"), ("assistant", '{"total": 3}')]
