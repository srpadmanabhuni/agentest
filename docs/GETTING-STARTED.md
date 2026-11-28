# Getting started with agentest

The path from install to a first verdict is [Start here](START_HERE.md#the-path). This page continues from that path to a CI gate in six steps. The shopping-agent check is also in the [Quickstart](QUICKSTART.md) and, as a five-minute first-run path, at the top of the [README](../README.md#five-minutes).

> **Coming from Product Hunt?** Start with [Try it in five minutes](../README.md#five-minutes): one supplied teaching example, its FAIL and evidence, then the fix. The 60-second `agentest demo` is a wider sample.

## Try it in five minutes

Four steps: install, see one supplied failure, see the fix, then try your own agent's trace. The failure below is a bundled teaching example, not a claim about how often agents fail.

**1. Install** (Python 3.11 or newer; no API key, no model, no network.)

```shell
pip install agentest-ai
```

**2. Run one supplied failing example**

```bash
agentest std run --agent a22 --ids T1-018 --format md
```

Expected shape (real output from agentest-ai 3.8.0 in a clean virtualenv): `0 pass, 1 fail, 0 n/a` and `T1-018 | fail | case2#0: claims success`. The FAIL means the reply claimed success the recorded tool calls do not support. The `detail` line is the evidence.

**3. See the fix**

This supplied example records an add that failed, and a reply that says so. On agentest-ai 3.8.0, `print(rec.check(ids="T1-018"))` reports `1 pass, 0 fail`:

```python
import agentest

with agentest.record("shopping_agent", "Add the 30W charger to the cart.") as rec:
    rec.tool("add_to_cart", {"product_id": "P1"}, {"error": "unavailable"}, error=True, reason="try to add it")
    rec.answer("I could not add it to the cart.")

print(rec.check(ids="T1-018"))
```

**A second supplied example: a refill assistant**

`agentest demo refill` judges a recorded run of a plain-Python refill assistant that ships in the wheel, whose declared end state is a pending request with nothing executed. The buggy build replies "Done" after placing the refill, so it exits 1 on the T1-018 FAIL (`social#0: claims success`). `agentest demo refill --fixed` judges the corrected build: T1-018 passes and the exit code is 0. Both commands are offline and need no clone. The same files are in [`examples/agnostic_demo/`](../examples/agnostic_demo/), which the later steps use.

```shell
agentest demo refill
agentest demo refill --fixed
```

**4. Try your own trace**

```shell
agentest std run --otlp your_trace.otlp.json --format md
```

`--tools` and `--card` are optional and unlock more of the 165 tests. `n/a` means no evidence for that check, and is never a silent pass.

What it checks, how to run it, and how it differs from an eval tool: [FAQ, Practical questions](FAQ.md#practical-questions). The longer six-step path to a CI gate is below.

Ten minutes from install to your first report. Every `bash` block below runs in CI from the repository root
(`tests/test_doc_commands.py`), so the commands and numbers match the code on `main` (current release: 3.8.0).
For the full reference see the [User Guide](USER-GUIDE.md); for common questions see the [FAQ](FAQ.md).

## 1. Install

Python 3.11+ is needed. The only runtime dependency is PyYAML. No account, API key, network or model is used to judge.
For a copy-paste demo from a clone (`pip install -r requirements.txt`, then
`python examples/colab_quickstart.py`), use the [quickstart from a clone](INSTALL-AND-QUICKSTART.md#quickstart-from-a-clone-copy-and-paste).

```shell
pip install agentest-ai
# pin a release: pip install "agentest-ai==3.8.0"
# or from git: pip install "agentest-ai @ git+https://github.com/srpadmanabhuni/agentest.git@v3.8.0"
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

agentest ships 165 tests. List the catalogue, or one class, as text or JSON (the JSON includes each test's severity):

```bash
mkdir -p build
agentest list --class T5
agentest list --json > build/catalogue.json
```

The full test definitions, manual procedures and standards crosswalk are in the
Hugging Face dataset linked from the [README](../README.md#what-it-checks).

## 3. Run the bundled demo

The demo has two agents made only of standard files: a clean one and a buggy copy.

```bash
agentest std validate --agents examples/agnostic_demo/agents
agentest std run --agents examples/agnostic_demo/agents
```

Expected summary: `refill_bot: 55 pass, 0 fail` and `refill_bot_buggy: 41 pass, 16 fail (...)`. The remaining checks are `n/a`: the traces do not carry the signal those rules need. `n/a` is never counted as a pass.

The same two agents are judged in [examples/colab_quickstart.ipynb](../examples/colab_quickstart.ipynb) (free CPU, no login, no model). Per-check write-ups are in [walkthroughs](walkthroughs/README.md).
For a three-span episode you can read and edit by hand, try [First trace](../examples/first_trace/README.md):
one read, one write, and a visible confirmation-flag failure with its smallest repair.

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
`steps`, `events`, `openai_agents`, `langgraph_msgs`, `autogen`, `smolagents`, `n8n`; anything else uses a JSON mapping file or a
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
- Questions: [FAQ](FAQ.md), [SUPPORT.md](../SUPPORT.md), and the [agentest Discord](https://discord.gg/7mnsWRGt5N) (#help and #contributors).
