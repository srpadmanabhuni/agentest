"""Haystack ChatMessage records are imported to the same verdicts as LangGraph."""
import json
from pathlib import Path

from agentest.cli import main
from agentest.standards.importers import adapt, is_write_from_tools

ROOT = Path(__file__).resolve().parents[1]
LG = ROOT / "examples" / "langgraph_import"
HY = ROOT / "examples" / "haystack_import"
CARD = LG / "agents" / "expense_bot" / "agent-card.json"
TOOLS = LG / "agents" / "expense_bot" / "tools.json"
MAPPING = json.loads((HY / "import" / "map.json").read_text())


def _rows():
    return [json.loads(line) for line in (HY / "native" / "expense_bot.jsonl").read_text().splitlines() if line.strip()]


def _episode(raw):
    return adapt(raw, MAPPING, is_write=is_write_from_tools(TOOLS), base=HY / "import")


def _verdicts(trace: Path, out: Path) -> dict:
    assert main([
        "std", "run", "--otlp", str(trace), "--card", str(CARD),
        "--tools", str(TOOLS), "--format", "json", "--out", str(out),
    ]) in (0, 1)
    return {row["id"]: row["status"] for row in json.loads(out.read_text())["results"]}


def test_haystack_example_matches_langgraph_verdicts(tmp_path):
    imported = tmp_path / "haystack.otlp.jsonl"
    assert main([
        "std", "import", str(HY / "native" / "expense_bot.jsonl"),
        "--map", str(HY / "import" / "map.json"),
        "--tools", str(TOOLS), "--service", "expense_bot", "--out", str(imported),
    ]) == 0

    got = _verdicts(imported, tmp_path / "haystack.json")
    want = _verdicts(
        LG / "agents" / "expense_bot" / "traces" / "expense_bot.otlp.jsonl",
        tmp_path / "langgraph.json",
    )
    assert len(got) == 130
    assert got == want
    assert any(status == "fail" for status in got.values())


def test_maps_tool_calls_results_and_application_state():
    ep = _episode(_rows()[0])

    assert [
        (call.name, call.arguments, call.call_id, call.result, call.error, call.side_effect)
        for call in ep.tool_calls
    ] == [
        ("get_policy", {"category": "travel"}, "call_1", '{"travel_limit": 5000}', False, "read"),
        (
            "submit_expense",
            {"amount": 640, "category": "travel", "note": "Pune client visit"},
            "call_2",
            "PENDING manager approval",
            False,
            "write",
        ),
    ]
    assert ep.final_answer == "Your INR 640 taxi expense is submitted and pending manager approval."
    assert [(item.kind, item.effect) for item in ep.state_changes] == [("pending", "submitted")]


def test_matches_tool_results_to_origin_ids_and_omits_reasoning():
    tool_a = {"tool_name": "lookup", "arguments": {"q": "policy"}, "id": "call-a", "extra": None}
    tool_b = {"tool_name": "submit", "arguments": {"amount": 10}, "id": "call-b", "extra": None}
    raw = {
        "agent": "expense_bot",
        "probe": "canon",
        "input": "check this expense",
        "trace": [
            {
                "role": "assistant",
                "name": "expense_bot",
                "content": [
                    {"reasoning": {"reasoning_text": "private reasoning", "extra": {}}},
                    {"text": "Checking."},
                    {"tool_call": tool_a},
                    {"tool_call": tool_b},
                ],
            },
            {
                "role": "tool",
                "content": [{
                    "tool_call_result": {
                        "result": "submitted",
                        "origin": tool_b,
                        "error": True,
                    }
                }],
            },
            {
                "role": "tool",
                "content": [{
                    "tool_call_result": {
                        "result": "policy found",
                        "origin": tool_a,
                        "error": False,
                    }
                }],
            },
        ],
        "output": {},
    }

    ep = _episode(raw)
    by_id = {call.call_id: call for call in ep.tool_calls}
    assert by_id["call-a"].result == "policy found"
    assert by_id["call-a"].error is False
    assert by_id["call-b"].result == "submitted"
    assert by_id["call-b"].error is True
    assert [message.content for message in ep.messages if message.role == "assistant"] == ["Checking."]
    assert "private reasoning" not in " ".join(message.content for message in ep.messages)


def test_rejects_a_tool_result_without_a_matching_call():
    raw = {
        "agent": "expense_bot",
        "probe": "canon",
        "input": "check",
        "trace": [{
            "role": "tool",
            "content": [{
                "tool_call_result": {
                    "result": "orphan",
                    "origin": {
                        "tool_name": "missing",
                        "arguments": {},
                        "id": "not-called",
                        "extra": None,
                    },
                    "error": False,
                }
            }],
        }],
        "output": {},
    }
    try:
        _episode(raw)
    except ValueError as exc:
        assert "no matching ToolCall" in str(exc)
    else:
        raise AssertionError("an orphan tool result must not be silently discarded")


def test_matches_repeated_tool_names_by_origin_arguments_when_id_is_absent():
    first = {"tool_name": "lookup", "arguments": {"key": "first"}, "id": None, "extra": None}
    second = {"tool_name": "lookup", "arguments": {"key": "second"}, "id": None, "extra": None}
    raw = {
        "agent": "expense_bot",
        "probe": "canon",
        "input": "look up two records",
        "trace": [
            {
                "role": "assistant",
                "content": [{"tool_call": first}, {"tool_call": second}],
            },
            {
                "role": "tool",
                "content": [{
                    "tool_call_result": {
                        "result": "second result",
                        "origin": second,
                        "error": False,
                    }
                }],
            },
            {
                "role": "tool",
                "content": [{
                    "tool_call_result": {
                        "result": "first result",
                        "origin": first,
                        "error": False,
                    }
                }],
            },
        ],
        "output": {},
    }

    ep = _episode(raw)
    assert [call.result for call in ep.tool_calls] == ["first result", "second result"]


def test_omits_image_and_file_payloads_from_tool_results():
    call = {"tool_name": "lookup", "arguments": {}, "id": "call-binary", "extra": None}
    raw = {
        "agent": "expense_bot",
        "probe": "canon",
        "input": "show the record",
        "trace": [
            {"role": "assistant", "content": [{"tool_call": call}]},
            {
                "role": "tool",
                "content": [{
                    "tool_call_result": {
                        "result": [
                            {"text": "record found"},
                            {"image": {"base64_image": "SENSITIVE_IMAGE_BYTES"}},
                            {"file": {"data": "SENSITIVE_FILE_BYTES", "mime_type": "application/pdf"}},
                        ],
                        "origin": call,
                        "error": False,
                    }
                }],
            },
        ],
        "output": {},
    }

    ep = _episode(raw)
    assert ep.tool_calls[0].result == "record found"
    assert ep.messages[-1].content == "record found"
    assert "SENSITIVE_" not in repr(ep.tool_calls)
    assert "SENSITIVE_" not in repr(ep.messages)
