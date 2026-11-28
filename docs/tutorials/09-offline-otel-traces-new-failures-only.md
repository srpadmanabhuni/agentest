# Tutorial 9: judge OpenTelemetry traces offline, and fail the build only on new failures

**Checks:** the default run, compared between two saved runs. **Agent:** the refund desk from [Tutorial 8](08-pytest-regression-from-a-failed-run.md). **Time:** 10 minutes. No model, no API key, no network.

You rarely adopt an evaluation suite on an agent that passes everything. Some checks already fail on day one, and a gate that goes red for ever gets switched off. This tutorial judges saved OpenTelemetry trace files offline, saves the verdicts as JSON, and uses `agentest std diff` so the build fails only when a check that used to pass now fails.

## 1. Setup

Python 3.11 or newer. Use the folder from Tutorial 8 (its steps 1 and 2 created `agent/` and `runs.py`), or follow those two steps in an empty folder first:

```bash
pip install agentest-ai
```

## 2. Save two runs as OpenTelemetry trace files

`rec.write(...)` saves a recorded run as an OTLP/JSON trace file. If your agent already exports OpenTelemetry GenAI traces, skip this step and use those files. Save this as `save_runs.py` and run `python save_runs.py`:

```python
from pathlib import Path

import agentest

from runs import LOOKUP_FIRST, SKIPPED_LOOKUP

AGENT = Path("agent")


def save(messages, out):
    results = {m["data"]["tool_call_id"]: m["data"]["content"] for m in messages if m["type"] == "tool"}
    with agentest.record("refund_desk", messages[0]["data"]["content"],
                         card=AGENT / "agent-card.json", tools=AGENT / "tools.json") as rec:
        for m in messages:
            if m["type"] == "ai":
                for call in m["data"].get("tool_calls", []):
                    rec.tool(call["name"], call["args"], results.get(call["id"]), call_id=call["id"],
                             reason="refund request from the user")
                if m["data"]["content"]:
                    rec.answer(m["data"]["content"])
    rec.write(out)


save(LOOKUP_FIRST, "before.otlp.jsonl")    # last release
save(SKIPPED_LOOKUP, "after.otlp.jsonl")   # a candidate change
```

## 3. Judge the baseline, and keep its verdicts

```bash
agentest std run --otlp before.otlp.jsonl --card agent/agent-card.json --tools agent/tools.json --json before.json
```

```text
otlp_agent: 23 pass, 2 fail (T2-004, T2-012)
total: 23 pass, 2 fail, 105 n/a over 1 agents x 130 IDs (examples)
```

Two checks already fail on the good run. Read why (add `--format md` to see the `detail` column): `issue_refund` ran without an approval step. The AgentCard declares no approval flow, so this is a real gap to decide about, not noise. Fix it later, or accept it for now. Either way you do not want it to block every pull request today. `105 n/a` means those checks found no evidence in the trace, which is not a pass.

Commit `before.json` to your repository as the baseline.

## 4. Judge the candidate and compare

```bash
agentest std run --otlp after.otlp.jsonl --card agent/agent-card.json --tools agent/tools.json --json after.json
agentest std diff before.json after.json --fail-on-new-fail
echo $?
```

```text
otlp_agent: 19 pass, 5 fail (T2-001, T2-002, T2-004, T2-012, T2-013)
total: 19 pass, 5 fail, 106 n/a over 1 agents x 130 IDs (examples)
newly failing: 3
newly passing: 0

otlp_agent
  T2-001  pass -> fail
  T2-002  pass -> fail
  T2-006  pass -> n/a
  T2-013  pass -> fail
1
```

The two old failures (T2-004, T2-012) are not reported: they were failing before. The three new ones are. The candidate refunds before it looks the order up, so the prerequisite checks flip, and `--fail-on-new-fail` exits 1. Read the transition column: `T2-006  pass -> n/a` is not a failure, but it tells you a check lost its evidence, which is worth a look.

Compare the other way round and the gate is green, because nothing newly fails:

```bash
agentest std diff after.json before.json --fail-on-new-fail
echo $?
```

```text
newly failing: 0
newly passing: 4
...
0
```

## 5. Put it in CI

Any CI system that can run two commands works. A shell step, with `baseline.json` committed:

```bash
agentest std run --otlp traces/*.otlp.jsonl --card agent/agent-card.json --tools agent/tools.json --json current.json
agentest std diff baseline.json current.json --fail-on-new-fail
```

When you fix a known failure, regenerate `baseline.json` in the same pull request so the new pass is locked in. For the GitHub Action, JUnit and SARIF versions of the same gate, see [Tutorial 4](04-ci-cd-github-actions.md).

## 6. Send verdicts back to your OpenTelemetry pipeline

`--emit-otlp` writes the verdicts as OTLP/JSON, one `gen_ai.evaluation.result` event per check with its name, label and explanation, so your existing observability tools can store and chart them:

```bash
agentest std run --otlp after.otlp.jsonl --card agent/agent-card.json --tools agent/tools.json --emit-otlp verdicts.otlp.json
```

## What to try next

- Point the same two commands at traces your agent already exports. The trace format and the minimum span attributes are in [Instrumenting an agent](../developers/INSTRUMENTING.md).
- Narrow the gate to the checks you care about with `--ids T2,T5-001`.
- A check that says `n/a` found no evidence. To unlock more checks, add the declarations they read, such as the AgentCard and the tools list.

Questions? Join us on [Discord](https://discord.gg/7mnsWRGt5N) in the #help channel.
