"""AI SDK UIMessage import: the offline example gives the same verdicts as the LangGraph message log."""
import json
from pathlib import Path

from agentest.cli import main
from agentest.standards.importers import adapt

ROOT = Path(__file__).resolve().parents[1]
LG = ROOT / "examples" / "langgraph_import"
AI = ROOT / "examples" / "ai_sdk_import"
CARD, TOOLS = LG / "agents" / "expense_bot" / "agent-card.json", LG / "agents" / "expense_bot" / "tools.json"
MAP = AI / "import" / "map.json"


def _verdicts(trace: Path, out: Path) -> dict:
    assert main(["std", "run", "--otlp", str(trace), "--card", str(CARD), "--tools", str(TOOLS), "--format", "json", "--out", str(out)]) in (0, 1)
    return {r["id"]: r["status"] for r in json.loads(out.read_text())["results"]}


def test_ai_sdk_example_matches_langgraph_verdicts(tmp_path):
    t = tmp_path / "ai.otlp.jsonl"
    assert main(["std", "import", str(AI / "native" / "expense_bot.jsonl"), "--map", str(MAP),
                 "--tools", str(TOOLS), "--service", "expense_bot", "--out", str(t)]) == 0
    got = _verdicts(t, tmp_path / "ai.json")
    want = _verdicts(LG / "agents" / "expense_bot" / "traces" / "expense_bot.otlp.jsonl", tmp_path / "l.json")
    assert len(got) == 130 and got == want
    assert any(v == "fail" for v in got.values())  # the social-engineering episode is still caught


def test_sample_keeps_the_ai_sdk_uimessage_shape():
    first = json.loads((AI / "native" / "expense_bot.jsonl").read_text(encoding="utf-8").splitlines()[0])
    message, part = first["trace"][1], first["trace"][1]["parts"][0]
    assert set(message) == {"id", "role", "parts"} and message["role"] == "assistant"
    assert part["type"] == "tool-get_policy" and part["state"] == "output-available"
    assert {"toolCallId", "input", "output"} <= set(part)


def _ep(messages, inp="do it"):
    return adapt({"agent": "a", "input": inp, "trace": messages}, {"dialect": "file:ai_sdk.py"}, base=AI / "import")


def test_tool_parts_map_to_calls_and_text_parts_to_replies():
    ep = _ep([
        {"id": "m0", "role": "user", "parts": [{"type": "text", "text": "do it", "state": "done"}]},
        {"id": "m1", "role": "assistant", "parts": [
            {"type": "tool-get_policy", "toolCallId": "c1", "state": "output-available",
             "input": {"category": "travel"}, "output": '{"travel_limit": 5000}'},
            {"type": "reasoning", "text": "check the policy first"},
        ]},
        {"id": "m2", "role": "assistant", "parts": [
            {"type": "tool-reimburse", "toolCallId": "c2", "state": "output-error",
             "input": {"amount": 640}, "errorText": "declined"}]},
        {"id": "m3", "role": "assistant", "parts": [{"type": "text", "text": "done", "state": "done"}]},
    ])
    assert [(c.name, c.arguments, c.call_id, c.result, c.error) for c in ep.tool_calls] == [
        ("get_policy", {"category": "travel"}, "c1", '{"travel_limit": 5000}', False),
        ("reimburse", {"amount": 640}, "c2", "declined", True),
    ]
    assert [(m.role, m.content) for m in ep.messages] == [("user", "do it"), ("user", "do it"), ("assistant", "done")]


def test_data_parts_are_not_replies_and_scalar_input_is_kept():
    ep = _ep([{"id": "m1", "role": "assistant", "parts": [
        {"type": "data-notes", "data": "not a reply"},
        {"type": "tool-log", "toolCallId": "c3", "state": "input-available", "input": "raw"},
    ]}])
    assert [(m.role, m.content) for m in ep.messages] == [("user", "do it")]
    assert [(c.name, c.arguments, c.result, c.error) for c in ep.tool_calls] == [("log", {"value": "raw"}, None, False)]
