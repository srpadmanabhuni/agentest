"""Google ADK event import: recorded sessions match the LangGraph reference."""
import json
from pathlib import Path

from agentest.cli import main
from agentest.standards.importers import adapt

ROOT = Path(__file__).resolve().parents[1]
LG = ROOT / "examples" / "langgraph_import"
ADK = ROOT / "examples" / "adk_import"
CARD = LG / "agents" / "expense_bot" / "agent-card.json"
TOOLS = LG / "agents" / "expense_bot" / "tools.json"


def _verdicts(trace: Path, out: Path) -> dict:
    assert main([
        "std", "run",
        "--otlp", str(trace),
        "--card", str(CARD),
        "--tools", str(TOOLS),
        "--format", "json",
        "--out", str(out),
    ]) in (0, 1)
    return {
        result["id"]: result["status"]
        for result in json.loads(out.read_text())["results"]
    }


def test_adk_example_matches_langgraph_verdicts(tmp_path):
    native = ADK / "native" / "expense_bot.jsonl"
    mapping = ADK / "import" / "map.json"
    imported = tmp_path / "adk.otlp.jsonl"

    assert main([
        "std", "import",
        str(native),
        "--map", str(mapping),
        "--tools", str(TOOLS),
        "--service", "expense_bot",
        "--out", str(imported),
    ]) == 0

    got = _verdicts(imported, tmp_path / "adk.json")
    want = _verdicts(
        LG / "agents" / "expense_bot" / "traces" / "expense_bot.otlp.jsonl",
        tmp_path / "langgraph.json",
    )

    assert len(got) == 130
    assert got == want
    assert any(status == "fail" for status in got.values())


def test_adk_function_calls_and_responses_are_mapped():
    native = ADK / "native" / "expense_bot.jsonl"
    mapping = json.loads((ADK / "import" / "map.json").read_text())
    raw = json.loads(native.read_text().splitlines()[0])

    episode = adapt(raw, mapping, base=ADK / "import")

    assert [call.name for call in episode.tool_calls] == [
        "get_policy",
        "submit_expense",
    ]
    assert episode.tool_calls[0].arguments == {"category": "travel"}
    assert episode.tool_calls[0].result == {"travel_limit": 5000}
    assert episode.tool_calls[1].arguments == {
        "amount": 640,
        "category": "travel",
        "note": "Pune client visit",
    }
    assert episode.tool_calls[1].result == "PENDING manager approval"

def test_adk_matches_response_without_call_id():
    mapping = json.loads(
        (ADK / "import" / "map.json").read_text(encoding="utf-8")
    )
    raw = {
        "agent": "expense_bot",
        "probe": "canon",
        "trace": [
            {
                "author": "expense_bot",
                "content": {
                    "parts": [
                        {"functionCall": {"name": "lookup", "args": {"q": "x"}}}
                    ]
                },
            },
            {
                "author": "lookup",
                "content": {
                    "parts": [
                        {"functionResponse": {"name": "lookup", "response": {"ok": True}}}
                    ]
                },
            },
        ],
    }

    episode = adapt(raw, mapping, base=ADK / "import")

    assert len(episode.tool_calls) == 1
    assert episode.tool_calls[0].name == "lookup"
    assert episode.tool_calls[0].result == {"ok": True}
    assert episode.tool_calls[0].error is False


def test_adk_marks_tool_errors_and_ignores_unmatched_responses():
    mapping = json.loads(
        (ADK / "import" / "map.json").read_text(encoding="utf-8")
    )
    raw = {
        "agent": "expense_bot",
        "probe": "canon",
        "trace": [
            None,
            {"author": "assistant", "content": {"parts": [None, {"text": "Working"}]}},
            {
                "author": "expense_bot",
                "content": {
                    "parts": [
                        {"functionCall": {"name": "submit_expense", "id": "call-1", "args": {}}}
                    ]
                },
            },
            {
                "author": "submit_expense",
                "error": True,
                "content": {
                    "parts": [
                        {"functionResponse": {"name": "submit_expense", "id": "call-1",
                                              "response": {"error": "Rejected"}}},
                        {"functionResponse": {"name": "unknown", "id": "missing",
                                              "response": {"ok": False}}},
                    ]
                },
            },
        ],
    }

    episode = adapt(raw, mapping, base=ADK / "import")

    assert len(episode.tool_calls) == 1
    assert episode.tool_calls[0].result == {"error": "Rejected"}
    assert episode.tool_calls[0].error is True
