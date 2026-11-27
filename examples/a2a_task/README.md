# A2A task example (`refund_helper`)

Install from PyPI:

```bash
pip install agentest-ai
```

Run it (from the repository root):

```bash
agentest std run --otlp examples/a2a_task/agent/traces/refund_helper.otlp.json --card examples/a2a_task/agent/agent-card.json --ids NT-010,NT-011,NT-012,NT-013,NT-014
```

Observed output (agentest 3.8.0, `--format md`):

```text
2 pass, 0 fail, 3 n/a over 1 agent(s).

| NT-010 | pass | 1 run(s): 3 hop(s) unchanged |
| NT-011 | pass | 1 run(s): 3 handover message(s) follow the declared schema |
| NT-012 | n/a | no standard signal: no agentest.task.ack_within_s with a sub-goal message that can be judged |
| NT-013 | n/a | no standard signal: no agentest.task.limits declared, or no declared limit reached |
| NT-014 | n/a | no standard signal: no agentest.task.autonomy_window_s, or every run ended inside its window |
```

Checks this example exercises: NT-010 and NT-011 are judged on this trace; NT-012, NT-013 and NT-014 have nothing to judge here, so they report n/a. NT-010 checks that the payload of every agent-to-agent message is unchanged between its send and receive spans; NT-011 checks that the handover messages follow the schema declared on the root span (`agentest.task.handover_schema`), in the order request, accept, result. See the [batch 2 notes](../../docs/new-tests/b2.md).

## What is in this folder

| Path | Role |
|---|---|
| [task.json](task.json) | The recorded A2A task: three messages (request, accept, result) and a completed status, plus the refund outcome artifact. |
| [mapping.json](mapping.json) | The mapping from the task to the spans in `agent/traces/refund_helper.otlp.json`. |
| [agent/traces/refund_helper.otlp.json](agent/traces/refund_helper.otlp.json) | The imported form of the task: one root span and one send and one receive span per message, with the `agentest.a2a.*` attributes from [TRACE-FORMAT.md](../../docs/TRACE-FORMAT.md). |
| [agent/agent-card.json](agent/agent-card.json) | The A2A AgentCard of the `refund_helper` agent (the same card as in [otel_plain](../otel_plain/agent-card.json)). |

The task is a refund for order ORD-7: the user asks for the refund, the agent accepts, and the refund ends pending approval, so the task completes. No tools are called in this task, so no `--tools` file is passed; the card's governance extension still describes the agent. All ids are example ids only.

No built-in `agentest std import` dialect reads an A2A Task (the dialects are `steps`, `openai_agents`, `langgraph_msgs`, `autogen`, `smolagents`, `n8n` and `events`), so the trace is committed as the imported form under `agent/traces/` and `mapping.json` records how it was derived from the task. See the [examples index](../README.md).
