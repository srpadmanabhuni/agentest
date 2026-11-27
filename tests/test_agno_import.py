"""Agno RunOutput messages import to the same verdicts as the equivalent LangGraph message log."""
import json
from pathlib import Path

from agentest.cli import main
from agentest.standards.importers import adapt

ROOT = Path(__file__).resolve().parents[1]
LG = ROOT / "examples" / "langgraph_import"
AG = ROOT / "examples" / "agno_import"
CARD, TOOLS = LG / "agents" / "expense_bot" / "agent-card.json", LG / "agents" / "expense_bot" / "tools.json"
MAP = AG / "import" / "map.json"


def _verdicts(trace: Path, out: Path) -> dict:
    assert main(["std", "run", "--otlp", str(trace), "--card", str(CARD), "--tools", str(TOOLS), "--format", "json", "--out", str(out)]) in (0, 1)
    return {r["id"]: r["status"] for r in json.loads(out.read_text())["results"]}


def test_agno_example_matches_langgraph_verdicts(tmp_path):
    t = tmp_path / "agno.otlp.jsonl"
    assert main(["std", "import", str(AG / "native" / "expense_bot.jsonl"), "--map", str(MAP),
                 "--tools", str(TOOLS), "--service", "expense_bot", "--out", str(t)]) == 0
    got = _verdicts(t, tmp_path / "agno.json")
    want = _verdicts(LG / "agents" / "expense_bot" / "traces" / "expense_bot.otlp.jsonl", tmp_path / "l.json")
    assert len(got) == 130 and got == want
    assert any(v == "fail" for v in got.values())  # the social-engineering episode is still caught


def test_sample_keeps_the_agno_message_shape():
    first = json.loads((AG / "native" / "expense_bot.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert [m["role"] for m in first["trace"]] == ["system", "user", "assistant", "tool", "assistant", "tool", "assistant"]
    request, result = first["trace"][2], first["trace"][3]
    assert request["tool_calls"][0]["type"] == "function" and isinstance(request["tool_calls"][0]["function"]["arguments"], str)
    assert {"tool_call_id", "tool_name", "tool_args", "tool_call_error", "content"} <= set(result)
    assert result["tool_call_id"] == request["tool_calls"][0]["id"]


def _ep(messages, inp="do it"):
    return adapt({"agent": "a", "input": inp, "trace": messages}, json.loads(MAP.read_text()), base=AG / "import")


def test_tool_calls_results_errors_and_replies():
    ep = _ep([
        {"role": "system", "content": "be careful"},
        {"role": "user", "content": "do it"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "lookup", "arguments": '{"q": "x"}'}},
            {"id": "c2", "type": "function", "function": {"name": "write", "arguments": '{"k": 1}'}}]},
        {"role": "tool", "content": "boom", "tool_call_id": "c2", "tool_name": "write", "tool_args": {"k": 1}, "tool_call_error": True},
        {"role": "tool", "content": "row 7", "tool_call_id": "c1", "tool_name": "lookup", "tool_args": {"q": "x"}, "tool_call_error": False},
        {"role": "user", "content": [{"type": "text", "text": "and then?"}]},
        {"role": "assistant", "content": "done"},
    ])
    assert [(c.name, c.arguments, c.call_id, c.result, c.error) for c in ep.tool_calls] == [
        ("lookup", {"q": "x"}, "c1", "row 7", False), ("write", {"k": 1}, "c2", "boom", True)]  # results paired by id
    assert [(m.role, m.content) for m in ep.messages] == [("user", "do it"), ("user", "and then?"), ("assistant", "done")]


def test_history_skipped_and_tool_message_without_request():
    ep = _ep([
        {"role": "user", "content": "old question", "from_history": True},
        {"role": "assistant", "content": "old answer", "from_history": True},
        {"role": "tool", "content": "PAID", "tool_call_id": "c9", "tool_name": "reimburse", "tool_args": {"amount": 1}},
    ])
    assert [(c.name, c.arguments, c.call_id, c.result, c.error) for c in ep.tool_calls] == [("reimburse", {"amount": 1}, "c9", "PAID", False)]
    assert [(m.role, m.content) for m in ep.messages] == [("user", "do it")]
