"""Compare the bundled LlamaIndex Workflow recording with the LangGraph recording."""

import json
from pathlib import Path

from agentest.cli import main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
LLAMAINDEX = EXAMPLES / "llamaindex_import"
EXPENSE_BOT = EXAMPLES / "langgraph_import" / "agents" / "expense_bot"
CARD = EXPENSE_BOT / "agent-card.json"
TOOLS = EXPENSE_BOT / "tools.json"


def _verdicts(trace: Path, output: Path) -> dict[str, str]:
    assert main([
        "std", "run", "--otlp", str(trace), "--card", str(CARD), "--tools", str(TOOLS),
        "--format", "json", "--out", str(output),
    ]) in (0, 1)
    return {row["id"]: row["status"] for row in json.loads(output.read_text(encoding="utf-8"))["results"]}


def test_llamaindex_example_matches_langgraph_verdicts(tmp_path):
    trace = tmp_path / "llamaindex.otlp.jsonl"
    assert main([
        "std", "import", str(LLAMAINDEX / "native" / "expense_bot.jsonl"),
        "--map", str(LLAMAINDEX / "import" / "map.json"),
        "--tools", str(TOOLS), "--service", "expense_bot", "--out", str(trace),
    ]) == 0

    llamaindex = _verdicts(trace, tmp_path / "llamaindex.json")
    langgraph = _verdicts(
        EXPENSE_BOT / "traces" / "expense_bot.otlp.jsonl", tmp_path / "langgraph.json",
    )
    assert llamaindex == langgraph
    assert {"pass", "fail"} <= set(llamaindex.values())
