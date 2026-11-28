"""Semantic Kernel's serialized chat history imports offline with LangGraph verdict parity."""

import json
from pathlib import Path

import pytest

from agentest.cli import main
from agentest.standards.importers import adapt, read_native, to_docs
from agentest.standards.otel import from_otlp

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
SK = EXAMPLES / "semantic_kernel_import"
LG = EXAMPLES / "langgraph_import" / "agents" / "expense_bot"
MAP = SK / "import" / "map.json"
NATIVE = SK / "native" / "expense_bot.jsonl"


@pytest.mark.parametrize("mode", ["examples", "strict"])
def test_semantic_kernel_example_matches_langgraph_verdicts(tmp_path, mode):
    trace = tmp_path / "semantic-kernel.otlp.jsonl"
    tools = ["--tools", str(LG / "tools.json")]
    assert main(["std", "import", str(NATIVE), "--map", str(MAP), *tools, "--service", "expense_bot", "--out", str(trace)]) == 0
    assert len(read_native(trace)) == 4
    common = ["--mode", mode, "--card", str(LG / "agent-card.json"), *tools, "--format", "json"]
    actual, expected = tmp_path / "actual.json", tmp_path / "expected.json"
    assert main(["std", "run", "--otlp", str(trace), *common, "--out", str(actual)]) == 0
    assert main(["std", "run", "--otlp", str(LG / "traces" / "expense_bot.otlp.jsonl"), *common, "--out", str(expected)]) == 0
    report = json.loads(actual.read_text(encoding="utf-8"))
    assert report == json.loads(expected.read_text(encoding="utf-8"))
    assert any(row["id"] == "T3-006" and row["status"] == "fail" for row in report["results"])


def _message(role, *items):
    return {"content_type": "message", "role": role, "items": list(items), "metadata": {}}


def _text(text):
    return {"content_type": "text", "text": text, "metadata": {}}


def test_tool_calls_results_errors_and_message_order():
    error = "An error occurred while invoking the function Expense-submit: ledger unavailable"
    malformed = "The tool call arguments are malformed. Arguments must be in JSON format. Please try again."
    raw = {"input": "check the expense", "history": {"messages": [
        _message("user", _text("check the expense")),
        _message("assistant", _text("Checking policy."), {
            "content_type": "function_call", "id": "c1", "name": "Policy-lookup",
            "function_name": "lookup", "plugin_name": "Policy", "arguments": '{"category": "travel"}',
        }, {
            "content_type": "function_call", "id": "item_2", "call_id": "c2",
            "function_name": "submit", "plugin_name": "Expense", "arguments": {"amount": 640},
        }),
        _message("tool", {
            "content_type": "function_result", "id": "item_2", "call_id": "c2", "result": error,
            "function_name": "submit", "plugin_name": "Expense",
        }),
        _message("tool", {
            "content_type": "function_result", "id": "c1", "result": '{"note": "no errors"}',
            "function_name": "lookup", "plugin_name": "Policy",
        }),
        _message("assistant", _text("Please confirm.")),
        _message("user", _text("Try again.")),
        _message("assistant", {
            "content_type": "function_call", "id": "c3", "name": "retry", "function_name": "retry", "arguments": "{bad",
        }, {
            "content_type": "function_call", "id": "c4", "name": "check", "function_name": "check", "arguments": "null",
        }),
        _message("tool", {
            "content_type": "function_result", "id": "c3", "result": malformed, "function_name": "retry",
        }, {
            "content_type": "function_result", "id": "c4", "result": "rejected", "function_name": "check",
            "metadata": {"exception": "LedgerClosed"},
        }),
        _message("assistant", _text("Unable to submit.")),
    ]}}
    mapping = json.loads(MAP.read_text(encoding="utf-8"))
    ep = adapt(raw, mapping, base=MAP.parent)
    expected = [
        ("Policy-lookup", {"category": "travel"}, "c1", '{"note": "no errors"}', False),
        ("Expense-submit", {"amount": 640}, "c2", error, True),
        ("retry", {"raw": "{bad"}, "c3", malformed, True),
        ("check", {"value": None}, "c4", "rejected", True),
    ]
    assert [(c.name, c.arguments, c.call_id, c.result, c.error) for c in ep.tool_calls] == expected
    assert [(m.role, m.content) for m in ep.messages[1:]] == [
        ("user", "check the expense"), ("assistant", "Checking policy."), ("tool", error),
        ("tool", '{"note": "no errors"}'), ("assistant", "Please confirm."), ("user", "Try again."),
        ("assistant", ""), ("tool", malformed), ("tool", "rejected"), ("assistant", "Unable to submit."),
    ]
    assert ep.messages[2].seq < ep.tool_calls[0].seq < ep.tool_calls[1].seq < ep.messages[3].seq
    assert ep.messages[6].seq < ep.tool_calls[2].seq < ep.messages[8].seq

    (document,) = to_docs([raw], mapping, service="example", base=MAP.parent)
    run = from_otlp(document)
    assert [(c.name, c.args, c.call_id, c.result, c.error) for c in run.tools] == expected
