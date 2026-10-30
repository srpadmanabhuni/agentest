# Reading an agentest report: actionable failures and n/a explanations

Every `fail` in an agentest report tells you **where** it happened, **which rule** it broke and **what to change**. Every `n/a` tells you **which field is missing** and **how to supply it**. This page shows how to read both.

## Get the guidance

```bash
# Markdown and HTML reports always include guidance
agentest std run --otlp traces/my_agent.otlp.jsonl --card agent-card.json --tools tools.json \
  --format md --out report.md

# JSON / JUnit / SARIF stay byte-identical by default; add --explain to include guidance
agentest std run --otlp traces/my_agent.otlp.jsonl --format junit --out agentest.xml --explain
```

## A failing check

Each failing row has four parts:

| Part | Example (from the bundled buggy demo agent) |
|---|---|
| **detail** – what was observed | `out of order: social#0:place_refill before ['verify_identity']` |
| **where** – run and span id | `social#0:place_refill span a0c0d81654835357` |
| **rule** – the universal rule, in words | Prerequisites published in the governance extension succeed before the dependent tool runs (every run). |
| **fix** – the condition to make true | For each tool call, every name in `DEPENDS_ON[name]` appears earlier in the trace with `succeeded == True`. |

Paste the span id into your trace viewer to jump straight to the offending call. A finding with no single span (for example a side-effect fence over the whole run) says `agent-level finding`.

Verdicts don't depend on report options: `--explain` adds text only and never changes a verdict.

## Why a check is n/a

`n/a` means the inputs contain no standard signal the check can judge. It isn't a pass. Run the linter to see what's missing and how many checks each fix would decide:

```bash
agentest std lint traces/my_agent.otlp.jsonl
```

Typical output (abridged):

```
8 run(s); 122 of 176 checks n/a
missing AgentCard / tools.json metadata: unlocks 36 check(s) ...; how: publish AgentCard skills, capabilities
  and the governance extension, or MCP tool annotations (readOnlyHint, destructiveHint, idempotentHint, enums)
missing agentest.approval spans: unlocks 7 check(s) ...; how: record each human or policy decision as an
  agentest.approval span (granted, approver, policy_version, reason)
missing error.type on the failing tool span: unlocks 5 check(s) ...; how: set error.type (and span status ERROR)
missing gen_ai.conversation.id across traces: unlocks 5 check(s) ...; how: record each turn as its own trace
  and share one gen_ai.conversation.id
```

The most common causes:

- **No AgentCard or tool list.** Start from `templates/my_agent/` (agent-card.json, tools.json, a sample trace).
- **No run exercises the situation.** For example, no run includes a failing step, so rollback checks can't be judged. Add a test input that covers that situation.
- **Missing standard fields.** These include final reply (`gen_ai.output.messages`), tool arguments (`gen_ai.tool.call.arguments`) and conversation id (`gen_ai.conversation.id`).

## Keep n/a honest in CI

Use `--max-na` so missing telemetry can't pass as a clean run:

```bash
agentest std run --otlp traces/ --strict --max-na 0.6 --format junit --out agentest.xml
```

The run fails if any agent's n/a share is above the threshold.

Questions: srinivas AT testAIng.com, or open a GitHub issue.
