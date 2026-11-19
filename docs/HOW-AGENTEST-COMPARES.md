# How agentest compares

agentest (agentest-ai) — deterministic OpenTelemetry evals for AI agents — judges recorded traces with rule-based checks. The table below contrasts that approach with two common alternatives, in generic terms: LLM-as-a-judge evaluation tools, and cloud observability platforms. It is a description of evaluation mode, not a ranking.

| Dimension | agentest | LLM-as-a-judge evaluation tools | Cloud observability platforms |
|---|---|---|---|
| Execution mode | Offline and deterministic. The same traces produce the same verdicts. No model is called at evaluation time. | Typically depend on a model, and often on a network, to score outputs. Verdicts can vary between runs. | Typically require a hosted account and ingested telemetry. |
| Evaluation target | Execution traces, tool-call order, state changes, and declared tool or agent metadata (OpenTelemetry GenAI spans, plus an optional A2A AgentCard and MCP tools list). | Often the final text: similarity, hallucination, or other output-quality scores. | Often monitoring, debugging and trace inspection. Evaluation, when present, is a separate feature. |
| Cost and latency | No model or API token cost at evaluation time. Runtime is local rule checks over the recorded trace. | Incur model token cost and added latency for each scored trace. | Incur platform usage costs. Latency depends on the hosted pipeline. |
| Standards and inputs | Reads OpenTelemetry GenAI traces, A2A AgentCards and MCP tool lists. | Vary by product. Inputs are often prompt and output pairs rather than tool-level traces. | Often traces and metrics. They do not necessarily read A2A AgentCards or MCP tool lists. |

Install the runner from PyPI (the import and the CLI stay `agentest`):

```bash
pip install agentest-ai
```

Then judge a recorded trace:

```bash
agentest std run --otlp my_traces.otlp.jsonl
```

## When not to use agentest

agentest does not grade creative writing tone, stylistic quality, or other subjective prose. If you only need a score of how a reply reads, this is the wrong tool.

It is also not a model leaderboard, and a passing run is not certification or a claim that an agent meets a regulation. Some free-text checks are deterministic English regex heuristics; they are uncalibrated.

Use agentest when you care about what the agent actually did: the tools it called, the order it called them, the state it left behind, and whether a success claim in the reply is backed by the trace.

## See also

- [FAQ](FAQ.md)
- [What are agentic evals?](what-are-agentic-evals.md)
- [User guide](USER-GUIDE.md)
