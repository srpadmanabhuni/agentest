"""Pydantic AI message history import: the offline example gives the same verdicts as the LangGraph message log."""
import json
from pathlib import Path

from agentest.cli import main
from agentest.standards.importers import adapt

ROOT = Path(__file__).resolve().parents[1]
LG = ROOT / "examples" / "langgraph_import"
PA = ROOT / "examples" / "pydanticai_import"
CARD, TOOLS = LG / "agents" / "expense_bot" / "agent-card.json", LG / "agents" / "expense_bot" / "tools.json"
MAP = PA / "import" / "map.json"


def _verdicts(trace: Path, out: Path) -> dict:
    assert main(["std", "run", "--otlp", str(trace), "--card", str(CARD), "--tools", str(TOOLS), "--format", "json", "--out", str(out)]) in (0, 1)
    return {r["id"]: r["status"] for r in json.loads(out.read_text())["results"]}


def test_pydanticai_example_matches_langgraph_verdicts(tmp_path):
    t = tmp_path / "pa.otlp.jsonl"
    assert main(["std", "import", str(PA / "native" / "expense_bot.jsonl"), "--map", str(MAP),
                 "--tools", str(TOOLS), "--service", "expense_bot", "--out", str(t)]) == 0
    got = _verdicts(t, tmp_path / "pa.json")
    want = _verdicts(LG / "agents" / "expense_bot" / "traces" / "expense_bot.otlp.jsonl", tmp_path / "l.json")
    assert len(got) == 130 and got == want
    assert any(v == "fail" for v in got.values())  # the social-engineering episode is still caught


def test_sample_keeps_the_pydanticai_message_shape():
    first = json.loads((PA / "native" / "expense_bot.jsonl").read_text(encoding="utf-8").splitlines()[0])
    request, response, returned = first["trace"][0], first["trace"][1], first["trace"][2]
    assert request["kind"] == "request" and request["parts"][0]["part_kind"] == "user-prompt"
    call = response["parts"][0]
    assert response["kind"] == "response" and call["part_kind"] == "tool-call"
    assert {"tool_name", "args", "tool_call_id"} <= set(call)
    ret = returned["parts"][0]
    assert ret["part_kind"] == "tool-return" and ret["tool_call_id"] == call["tool_call_id"] and ret["outcome"] == "success"


def _ep(messages, inp="do it"):
    return adapt({"agent": "a", "input": inp, "trace": messages}, {"dialect": "file:pydanticai_adapter.py"}, base=PA / "import")


def test_calls_pair_with_returns_by_id_and_failed_outcomes_are_errors():
    ep = _ep([
        {"kind": "request", "parts": [{"part_kind": "system-prompt", "content": "be terse"},
                                      {"part_kind": "user-prompt", "content": "do it"}]},
        {"kind": "response", "parts": [
            {"part_kind": "thinking", "content": "look up first"},
            {"part_kind": "tool-call", "tool_name": "lookup", "args": '{"q": "x"}', "tool_call_id": "c1"},
            {"part_kind": "tool-call", "tool_name": "write", "args": {"k": 1}, "tool_call_id": "c2"}]},
        {"kind": "request", "parts": [
            {"part_kind": "tool-return", "tool_name": "write", "content": "boom", "tool_call_id": "c2", "outcome": "failed"},
            {"part_kind": "tool-return", "tool_name": "lookup", "content": {"row": 7}, "tool_call_id": "c1"}]},
        {"kind": "response", "parts": [{"part_kind": "text", "content": "done"}]},
    ])
    assert [(c.name, c.arguments, c.call_id, c.result, c.error) for c in ep.tool_calls] == [
        ("lookup", {"q": "x"}, "c1", {"row": 7}, False), ("write", {"k": 1}, "c2", "boom", True)]
    assert [(m.role, m.content) for m in ep.messages] == [("user", "do it"), ("assistant", "done")]  # prompts, thinking skipped


def test_retry_prompt_output_tool_and_follow_up_prompt():
    ep = _ep([
        {"kind": "response", "parts": [{"part_kind": "tool-call", "tool_name": "lookup", "args": "", "tool_call_id": "c1"}]},
        {"kind": "request", "parts": [{"part_kind": "retry-prompt", "tool_name": "lookup", "content": "q is required",
                                       "tool_call_id": "c1"},
                                      {"part_kind": "user-prompt", "content": ["follow-up question", {"kind": "image-url", "url": "x"}]}]},
        {"kind": "response", "parts": [{"part_kind": "tool-call", "tool_name": "final_result", "args": {"total": 3},
                                        "tool_call_id": "c2"}]},
        {"kind": "request", "parts": [{"part_kind": "tool-return", "tool_name": "final_result",
                                       "content": "Final result processed.", "tool_call_id": "c2"}]},
    ])
    assert [(c.name, c.arguments, c.result, c.error) for c in ep.tool_calls] == [("lookup", {}, "q is required", True)]
    assert [(m.role, m.content) for m in ep.messages] == [
        ("user", "do it"), ("user", "follow-up question"), ("assistant", '{"total": 3}')]
