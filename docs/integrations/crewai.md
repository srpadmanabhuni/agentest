# CrewAI: judge a crew's recorded run

agentest scores **recorded traces**, not your crew code. Your crew never imports agentest. This page shows the whole loop on a real recorded CrewAI run that ships in this repository, then how to do the same with your own crew.

There is no built-in CrewAI import dialect yet, so for your own crew you either export OpenTelemetry GenAI spans or write a small adapter (both below).

## 1. Try it on a real CrewAI run (about 10 seconds)

The folder `agents/a65/` is a CrewAI research-brief crew (a researcher and an editor, with a code check that each claim is quoted verbatim from a source) run once per case with a local open model (Qwen2.5-7B-Instruct, CPU). Python 3.11 or newer, no API key, no network, no model:

```shell
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git && cd agentest
python3 -m venv .venv && . .venv/bin/activate && python -m pip install -q -e .
agentest std run --agent a65 --ids T1-001 --format md
```

Output:

```text
| ID | status | detail |
|---|---|---|
| T1-001 | fail | case0: unmet: output.published eq executed |
```

What it means: for case 0 (the input "Electric two-wheeler market in India: sales and buyer concerns") the crew's own success condition was that the brief is published. The recorded run ended with an empty answer and nothing published, so the check fails and names the unmet condition. The Hugging Face notes for this agent (defect D-35) say the code check rejected a promotional claim and left only one verified claim.

For contrast, `agentest std run --agent a09` judges a different recorded CrewAI crew and prints `a09: 13 pass, 0 fail` (the other checks are `n/a` because that trace has no signal for them; `n/a` is not a pass).

These are single recorded runs, not failure rates, and not a verdict on CrewAI. Other recorded CrewAI runs in `agents/`: `a18` (hierarchical process), `a24`, `a27`, `a38`, `a46`, `a51`, `a57` (Flows).

## 2. Judge your own crew

Pick one route.

**A. Export OpenTelemetry GenAI spans (preferred).** If your crew is already instrumented with an OpenTelemetry GenAI instrumentation, export the spans to a file (Collector `file` exporter) or send them to `agentest std serve`, then:

```shell
agentest std run --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json
```

agentest reads one trace per crew run: a root `invoke_agent` span, and one `execute_tool` span per tool call with `gen_ai.tool.name`, `gen_ai.tool.call.arguments` and `gen_ai.tool.call.result`. The exact attributes and the optional extras are in [Instrumenting your agent](../developers/INSTRUMENTING.md). The [AgentCard](../developers/AGENT-CARD.md) and `tools.json` (read-only versus state-changing hints) are small JSON files you write once; `agents/a65/` has working examples of both.

**B. Convert a log you already keep.** Dump each task's tool calls to JSON and map them with a `file:my_dialect.py` adapter, the same route the LangGraph and smolagents examples use: [Author Guide, section 3](../AUTHOR-GUIDE.md#3-a-framework-adapter), then `agentest std import --dialect file:my_dialect.py`.

## What is not here yet

- A CrewAI-specific importer and a runnable "emit spans from a live crew" example. Both need a CrewAI install and a model endpoint to test against real output, and we do not publish untested code. If you have a redacted CrewAI trace you can share, a [Contributing](../../CONTRIBUTING.md) issue with it is the fastest way to get this built.
- Judging is only as good as the signal in the trace. Checks that find none return `n/a`.

## Next

- [Getting started](../GETTING-STARTED.md) for the six-step path to a CI gate.
- [LangGraph integration](langgraph.md) and [OpenAI Agents SDK](openai-agents-sdk.md) for the same loop on other frameworks.
