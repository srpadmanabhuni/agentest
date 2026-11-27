# MCP proxy-log import example

An offline example that converts an out-of-process MCP proxy log (capturing every `tools/call` attempt on the wire, including pre-execution JSON-RPC `-32602` rejections and changed-argument retries that an in-process agent might skip logging) into OpenTelemetry GenAI `execute_tool` spans for `agentest`.

The sample trace in `native/proxy.jsonl` uses offline fixture IDs (`ORD-1001`, `mcp-1..3`) in the [`epistemic-guard`](https://github.com/AlienatedAliens/epistemic-guard) `ReceiptLogEntry` JSONL shape (the adapter in `import/mcp_proxy_map.py` also accepts raw JSON-RPC 2.0 `tools/call` request + result/error lines):

1. `check_eligibility` (`ok=true, executed=true`)
2. `book_ticket(qty=2)` rejected pre-execution with `-32602` (`ok=false, executed=false`)
3. `book_ticket(qty=1)` retried with a silently changed argument (`ok=true, executed=true`)

## Run offline

```shell
agentest std import examples/mcp_proxy_import/native/proxy.jsonl \
    --map examples/mcp_proxy_import/import/map.json \
    --tools examples/mcp_proxy_import/tools.json \
    --service ticket_bot --out build/mcp_proxy.otlp.jsonl
agentest std run --otlp build/mcp_proxy.otlp.jsonl \
    --tools examples/mcp_proxy_import/tools.json
```

## Point it at your own proxy log

Wrap your proxy JSONL lines in one episode record (`{"agent": ..., "probe": ..., "input": ..., "trace": [...], "output": {"final_answer": ...}}`) where `trace` holds either `epistemic-guard` `ReceiptLogEntry` objects or raw JSON-RPC 2.0 `tools/call` request/response dicts, then pass `--map examples/mcp_proxy_import/import/map.json` and your server's `tools/list` JSON.
