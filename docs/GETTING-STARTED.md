# Getting started with agentest

Ten minutes from install to your first report. Every `bash` block below runs in CI from the repository root
(`tests/test_doc_commands.py`), so the commands and numbers match the code on `main` (version 3.3.2).
For the full reference see the [User Guide](USER-GUIDE.md); for common questions see the [FAQ](FAQ.md).

## 1. Install

Python 3.11+ is needed. The only runtime dependency is PyYAML. No account, API key, network or model is used to judge.

```shell
# pip install agentest-ai   (PyPI: pending, not live yet; until then use the git line below)
pip install "agentest-ai @ git+https://github.com/srpadmanabhuni/agentest.git@v3.3.2"
```

To follow the examples below, work from a clone:

```shell
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
```

Check the install:

```bash
agentest version
```

## 2. Look at the catalogue

agentest judges 130 checks: the 110 catalogue IDs (classes `T1`–`T7`) plus 20 repo extensions (`X-001`…`X-020`).
List the catalogue, or one class, as text or JSON (the JSON includes each test's severity):

```bash
mkdir -p build
agentest list --class T5
agentest list --json > build/catalogue.json
```

The full test definitions, manual procedures and standards crosswalk are in the
Hugging Face dataset linked from the [README](../README.md#catalogue).

## 3. Run the bundled demo

The demo has two agents made only of standard files: a clean one and a buggy copy.

```bash
agentest std validate --agents examples/agnostic_demo/agents
agentest std run --agents examples/agnostic_demo/agents
```

Expected summary: `refill_bot: 55 pass, 0 fail` and `refill_bot_buggy: 41 pass, 16 fail (...)`. The rest of the
130 IDs are `n/a`: the traces do not carry the signal those rules need. `n/a` is never counted as a pass.

The same two agents are judged in [examples/colab_quickstart.ipynb](../examples/colab_quickstart.ipynb) (free CPU, no login, no model). Per-check write-ups are in [walkthroughs](walkthroughs/README.md).

## 4. Run it on your own agent

agentest does not run your agent. It reads what your agent already recorded:

| Input | Required? | What it gives the rules |
|---|---|---|
| OpenTelemetry GenAI traces (OTLP/JSON or protobuf) | yes | the run: messages, tool calls, results |
| A2A AgentCard (`agent-card.json`) | optional | skills, examples, governance extension |
| MCP tools list (`tools.json`) | optional | which tools are read-only or destructive |

If your agent already emits OpenTelemetry, point a file exporter at a file and run on it. This example writes a
trace with the Python standard library only, so you can see the expected shape:

```bash
mkdir -p build
python examples/otel_plain/emit_trace.py > build/trace.otlp.json
agentest std run --otlp build/trace.otlp.json \
    --card examples/otel_plain/agent-card.json --tools examples/otel_plain/tools.json
```

If your agent is not instrumented, convert its native log once with `agentest std import`. Built-in dialects:
`steps`, `events`, `openai_agents`, `langgraph_msgs`, `autogen`, `n8n`; anything else uses a JSON mapping file or a
small Python adapter ([Author Guide §3](AUTHOR-GUIDE.md#3-a-framework-adapter)).

```bash
agentest std import examples/agnostic_demo/native/refill_bot.jsonl \
    --map examples/agnostic_demo/import/map.json \
    --tools examples/agnostic_demo/agents/refill_bot/tools.json \
    --service refill_bot --out build/refill_bot.otlp.jsonl
agentest std run --otlp build/refill_bot.otlp.jsonl \
    --card examples/agnostic_demo/agents/refill_bot/agent-card.json \
    --tools examples/agnostic_demo/agents/refill_bot/tools.json
```

You can also receive spans live from any OTLP/HTTP exporter with `agentest std serve --out build/inbox --port 4319`.

## 5. Read the report

Each agent × check gets `pass`, `fail` or `n/a`, and `detail` names the evidence or the missing signal.
Limit the report to some checks with `--ids`, or switch to `--mode strict` to use only standard fields:

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --ids T1-002,T1-004
agentest std run --agents examples/agnostic_demo/agents --mode strict --format md --out build/report.md
```

Many `n/a` results? See [Why are so many of my checks n/a?](FAQ.md#verdicts).

## 6. Add it to CI

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot \
    --format junit --out build/agentest.xml --strict
```

`--strict` exits with status 1 if any verdict is `fail`. Other formats: `json`, `sarif`, `md`, `html`, `csv`.
See [CI](developers/CI.md) for a workflow example.

## Next steps

- Onboard a real agent folder end to end: [ONBOARDING](developers/ONBOARDING.md).
- Turn `n/a` into real checks: [INSTRUMENTING](developers/INSTRUMENTING.md) and the
  [governance extension](standards/EXTENSION.md).
- Write a new rule or adapter: [Author Guide](AUTHOR-GUIDE.md).
- Questions: [FAQ](FAQ.md) and [SUPPORT.md](../SUPPORT.md).
