# How to test MCP (Model Context Protocol) servers with OpenTelemetry and agentest

agentest (agentest-ai) — deterministic OpenTelemetry evals for AI agents.

agentest does not start or host an MCP server, and it does not speak the MCP transport. It judges what an agent did with MCP tools you already recorded: the server's `tools/list` result, plus OpenTelemetry GenAI `execute_tool` spans for each `tools/call`.

## What to capture

1. Save the MCP server's `tools/list` result as JSON (for example `tools.json`). Annotations such as `readOnlyHint`, `destructiveHint`, `idempotentHint` and `openWorldHint` are what several checks read.
2. Wrap each `tools/call` in an `execute_tool` span with `gen_ai.tool.name`, `gen_ai.tool.call.arguments` and `gen_ai.tool.call.result`. How to emit those spans is in [Instrumenting your agent](../developers/INSTRUMENTING.md).
3. Optionally save the A2A AgentCard as `agent-card.json` ([Writing the AgentCard](../developers/AGENT-CARD.md)).

## Judge a recorded run

```bash
pip install agentest-ai
agentest std run --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json
```

`--card` and `--tools` are optional. Checks that need a declared fact (for example which tools are read-only, or which tools are allowed) report `n/a` when that file is missing; `n/a` is not a pass.

If your agent already lives in an agent folder (`agent-card.json`, `tools.json`, `traces/*.otlp.jsonl`):

```bash
agentest std run --agents path/to/agents --agent my_mcp_agent --format md
```

To fail a CI job when any check fails:

```bash
agentest std run --otlp traces.otlp.jsonl --tools tools.json --format junit --out agentest.xml --strict
```

## What the checks look at

Checks use the MCP tools list together with the recorded spans. Typical signals include:

- tool names that appear in the trace but not on the declared list (unauthorized tool use)
- state-changing calls (`readOnlyHint` is false, or the tool is undeclared) without the confirmation or approval the check requires
- injected or extra recipients and disallowed hosts on write tools
- arguments or results that leak restricted data

The exact rule for each ID is in the [per-test guide](../testers/PER-TEST-GUIDE.md).

## Capturing calls from a proxy log

If the agent process skips emitting an OpenTelemetry span on a rejected call (such as JSON-RPC `-32602` invalid params) or a changed-argument retry, capture `tools/call` wire traffic out of process with an MCP proxy (for example `epistemic-guard mcp-proxy` / `mcp-http-proxy`) and import the proxy JSONL offline with `agentest std import`. See the worked offline example in [`examples/mcp_proxy_import/`](../../examples/mcp_proxy_import/README.md).

## See also

- [Instrumenting your agent](../developers/INSTRUMENTING.md)
- [Writing the AgentCard](../developers/AGENT-CARD.md)
- [User guide](../USER-GUIDE.md)
- [Getting started](../GETTING-STARTED.md)
