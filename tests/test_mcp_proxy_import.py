"""MCP proxy-log import example: rejected (-32602) calls and changed-arg retries both become spans."""

from __future__ import annotations

import json
from pathlib import Path

from agentest.cli import main
from agentest.standards.importers import adapt

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples" / "mcp_proxy_import"
NATIVE = EX / "native" / "proxy.jsonl"
MAP = EX / "import" / "map.json"
TOOLS = EX / "tools.json"


def test_mcp_proxy_import_preserves_rejected_and_retried_spans(tmp_path: Path) -> None:
    out_otlp = tmp_path / "mcp_proxy.otlp.jsonl"
    assert (
        main(
            [
                "std",
                "import",
                str(NATIVE),
                "--map",
                str(MAP),
                "--tools",
                str(TOOLS),
                "--service",
                "ticket_bot",
                "--out",
                str(out_otlp),
            ]
        )
        == 0
    )

    spans = []
    for line in out_otlp.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        doc = json.loads(line)
        for rs in doc.get("resourceSpans") or []:
            for ss in rs.get("scopeSpans") or []:
                spans.extend(ss.get("spans") or [])

    tool_spans = [
        sp
        for sp in spans
        if any(
            a.get("key") == "gen_ai.operation.name"
            and (a.get("value") or {}).get("stringValue") == "execute_tool"
            for a in (sp.get("attributes") or [])
        )
    ]
    assert len(tool_spans) == 3

    def _attr(sp: dict, key: str) -> str:
        for a in sp.get("attributes") or []:
            if a.get("key") == key:
                v = a.get("value") or {}
                return str(v.get("stringValue", v.get("intValue", "")))
        return ""

    names = [_attr(sp, "gen_ai.tool.name") for sp in tool_spans]
    assert names == ["check_eligibility", "book_ticket", "book_ticket"]

    # Second span is the -32602 pre-execution rejection: must carry ERROR status (code == 2)
    rejected_sp = tool_spans[1]
    assert (rejected_sp.get("status") or {}).get("code") == 2
    assert '"qty": 2' in _attr(rejected_sp, "gen_ai.tool.call.arguments")
    assert "-32602" in _attr(rejected_sp, "gen_ai.tool.call.result")

    # Third span is the changed-argument retry (qty=1)
    retried_sp = tool_spans[2]
    assert '"qty": 1' in _attr(retried_sp, "gen_ai.tool.call.arguments")

    # Confirm std run executes cleanly offline on the imported spans
    out_report = tmp_path / "report.json"
    assert (
        main(
            [
                "std",
                "run",
                "--otlp",
                str(out_otlp),
                "--tools",
                str(TOOLS),
                "--format",
                "json",
                "--out",
                str(out_report),
            ]
        )
        in (0, 1)
    )
    assert out_report.is_file()


def test_mcp_proxy_raw_jsonrpc_pair_mapping() -> None:
    mapping = json.loads(MAP.read_text(encoding="utf-8"))
    ep = adapt(
        {
            "agent": "ticket_bot",
            "probe": "retry_drift",
            "input": "Book 2 tickets",
            "trace": [
                {
                    "jsonrpc": "2.0",
                    "id": "req-1",
                    "method": "tools/call",
                    "params": {"name": "book_ticket", "arguments": {"qty": 2}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": "req-1",
                    "error": {"code": -32602, "message": "Invalid params"},
                },
                {
                    "jsonrpc": "2.0",
                    "id": "req-2",
                    "method": "tools/call",
                    "params": {"name": "book_ticket", "arguments": {"qty": 1}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": "req-2",
                    "result": {"content": [{"type": "text", "text": '{"booked": true}'}]},
                },
            ],
            "output": {"final_answer": "Booked your tickets."},
        },
        mapping,
        base=MAP.parent,
    )
    assert len(ep.tool_calls) == 2
    assert ep.tool_calls[0].name == "book_ticket" and ep.tool_calls[0].error is True
    assert ep.tool_calls[0].arguments == {"qty": 2}
    assert ep.tool_calls[1].name == "book_ticket" and ep.tool_calls[1].error is False
    assert ep.tool_calls[1].arguments == {"qty": 1}
