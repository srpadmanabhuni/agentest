# agentest User Guide (v3.4)

This guide is for people who **run** agentest against an agent: testers, QA leads, platform and CI owners.
If you want to add a rule, an adapter or a reference agent, read the [Author Guide](AUTHOR-GUIDE.md).

agentest judges an agent from three standard artifacts and nothing else:

| artifact | standard | file |
|:--|:--|:--|
| what the agent is and may do | A2A **AgentCard** (plus the optional governance extension `urn:agentest:a2a-ext:governance:v1`) | `agent-card.json` |
| what each tool does | MCP **tools/list** with tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) | `tools.json` |
| what the agent actually did | OpenTelemetry **GenAI** spans, OTLP/JSON or OTLP/protobuf | `traces/*.otlp.jsonl` |

The same 130 universal rules run on every agent. No rule names an agent, a tool, a framework or a vendor; there are
no per-agent profiles. Every command in a `bash` block below is executed by `tests/test_doc_commands.py`, from the
repository root, so the guide cannot drift from the code.

## 1. Install

From PyPI-style wheel or a fresh clone. Python 3.11+; the only required dependency is PyYAML.

```shell
git clone https://github.com/srpadmanabhuni/agentest.git
cd agentest
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"        # or: pip install .   (no dev tools)
```

These install commands are checked by the CI fresh-clone and wheel jobs. Check the install:

```bash
mkdir -p build/guide
agentest version
agentest std catalog --format csv --out build/guide/catalog.csv
head -3 build/guide/catalog.csv
```

## 2. Quickstart on your own traces

You need one OTLP trace file. If your agent is already instrumented with OpenTelemetry GenAI, export its spans to a
file (any OTLP file exporter, or `agentest std serve`, section 5). To see the exact shape, generate one with the
standard library only:

```bash
python examples/otel_plain/emit_trace.py > build/guide/trace.otlp.json
agentest std run --otlp build/guide/trace.otlp.json \
                 --card examples/otel_plain/agent-card.json --tools examples/otel_plain/tools.json
```

`--card` and `--tools` are optional. Without them the rules that need a declared fact (for example "which tools
change state") report `n/a`, never `pass`. Add them as soon as you can: the more you declare, the more is judged.

To judge a folder of agents, give each agent a directory with the three standard files:

```text
my_agents/
  billing_bot/
    agent-card.json      # A2A AgentCard
    tools.json           # MCP tools/list result
    traces/              # one or more *.otlp.jsonl / *.json / *.pb files
```

```bash
agentest std validate --agents examples/agnostic_demo/agents
agentest std run --agents examples/agnostic_demo/agents
```

`validate` checks the AgentCard and MCP metadata (and the governance extension against its
[JSON Schema](../src/agentest/standards/schemas/governance-extension.schema.json)) before you spend time on verdicts.

## 3. Modes: strict and examples

| mode | reads | use it for |
|:--|:--|:--|
| `strict` | only standard OTel / A2A / MCP fields and the governance extension | audits, gates, comparisons between agents |
| `examples` (default) | also the AgentCard `skills[].examples` to label which input a run answers | day-to-day runs, more IDs decided |

```bash
agentest std run --agents examples/agnostic_demo/agents --mode strict
agentest std run --agents examples/agnostic_demo/agents --mode examples
```

## 4. CLI reference

All commands are `agentest std <action> [options]`.

| action | what it does |
|:--|:--|
| `validate` | check AgentCard, MCP tools and governance extension of every agent folder |
| `run` | judge the traces; prints a summary, or writes a report with `--format` / `--out` |
| `import` | convert a native framework log into OTel GenAI OTLP/JSON (`--dialect` or `--map`) |
| `serve` | a standard-library OTLP/HTTP receiver (JSON and protobuf) that stores incoming traces as files |
| `export` | write the traces of every agent as OTLP/JSON |
| `gen` | list the probe inputs the rules would like to see for each agent (what to record next) |
| `regress` | compare a run with the checked-in baseline of the bundled agents |
| `catalog` | the 130 test IDs as JSON or CSV |

| option | for | meaning |
|:--|:--|:--|
| `--agents DIR` | all | directory of agent folders (default `agents/`, the bundled reference agents) |
| `--agent ID` | all | one agent folder only |
| `--otlp FILES` | run | judge plain OTLP files instead of agent folders (`.json`, `.jsonl`, `.pb`) |
| `--card`, `--tools` | run, import | AgentCard / MCP tools for `--otlp` and `import` |
| `--ids A,B` | run | report only these test IDs |
| `--mode` | run | `strict` or `examples` |
| `--format` | run, catalog | `json`, `junit`, `sarif`, `md`, `html`, `csv` |
| `--out FILE` | run, import, export, serve | where to write |
| `--json FILE` | run, regress | also write the raw verdict matrix |
| `--strict` | run | exit status 1 if any verdict is `fail` (for CI gates) |
| `--emit-otlp FILE` | run | also write the verdicts as OTel `gen_ai.evaluation.result` events |
| `--config FILE` | all | YAML/JSON config (section 6) |
| `--rules-dir DIR` | all | import extra rules from `*.py` files in DIR |
| `--dialect`, `--map`, `--service` | import | native log format, mapping file, service name |
| `--host`, `--port`, `--max-requests` | serve | bind address, port (default 4318), stop after N requests |
| `--judge URL` | run, regress | OpenAI-compatible endpoint for the semantic part of checks (`local` = llama.cpp default, `off` = none); default `$AGENTEST_JUDGE_URL` |
| `--judge-model`, `--judge-cache`, `--judge-offline` | run, regress | judge model name, answer cache, replay cached answers only |
| `--floor N` | regress | exit 1 when fewer than N baseline defects are caught (without a judge: caught + not assessed) |

Run only some IDs:

```bash
agentest std run --agents examples/agnostic_demo/agents --ids T2-001,T3-001,T5-006
```

## 5. Getting traces in

**Already OTel-instrumented.** agentest reads the GenAI semantic conventions pinned in
[semconv.yaml](../src/agentest/standards/semconv.yaml) (semconv 1.42.0 plus the GenAI repository commit) and maps
older convention versions (1.26 to 1.36 attributes and events) and the common instrumentation styles (OpenLLMetry,
OpenInference) onto them. `tests/test_otel_conformance.py` proves that the same behaviour written in each style gives
the same verdicts.

**Collect over the network.** Point any OTLP/HTTP exporter at `agentest std serve`; it accepts
`application/json` and `application/x-protobuf` on `/v1/traces` and appends the spans to
`<out>/<service.name>/traces/<service.name>.otlp.jsonl`, one agent folder per service (add `agent-card.json` and
`tools.json` next to `traces/` and it is ready for `--agents`):

```bash
agentest std serve --out build/guide/inbox --port 4319 --max-requests 1 &
sleep 1
curl -s -X POST -H 'Content-Type: application/json' \
     --data-binary @build/guide/trace.otlp.json http://127.0.0.1:4319/v1/traces
wait
agentest std run --otlp build/guide/inbox/*/traces/*.otlp.jsonl --card examples/otel_plain/agent-card.json --tools examples/otel_plain/tools.json
```

In production, set `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://HOST:4318/v1/traces` on the agent.

SDK exporters send one trace in several batches and retry on errors: spans of the same `traceId` are merged into one
run, ordered by start time, and a re-sent span (same `spanId`) counts once. The folder name comes from `service.name`
with unsafe characters replaced, so it cannot point outside `--out`. Bodies over 64 MB are rejected.

**Convention version.** If the traces declare `schemaUrl` (for example `https://opentelemetry.io/schemas/1.42.0`),
`validate` and `run` print a note when it is newer than the pinned 1.42.0 or not an OpenTelemetry schema; verdicts do not
change, attributes are read through the version table.

**Protobuf decoder.** OTLP/protobuf is decoded by a standard-library codec. To use the OpenTelemetry project's own
decoder instead, `pip install "agentest[otlp]"` and set `AGENTEST_OTLP_PROTOBUF=official`; both give the same result
(`tests/test_otel_sdk_conformance.py`, which also exports with the real OTel SDK when `agentest[conformance]` is installed).
PyYAML stays the only required dependency.

**Not instrumented.** Convert the native log once with `agentest std import`. Built-in dialects: `steps`, `events`,
`openai_agents`, `langgraph_msgs`, `autogen`, `n8n`; anything else uses a small mapping file or a `file:my.py`
adapter (see the [Author Guide](AUTHOR-GUIDE.md#3-a-framework-adapter)):

```bash
agentest std import examples/agnostic_demo/native/refill_bot.jsonl \
    --map examples/agnostic_demo/import/map.json \
    --tools examples/agnostic_demo/agents/refill_bot/tools.json \
    --service refill_bot --out build/guide/refill_bot.otlp.jsonl
agentest std run --otlp build/guide/refill_bot.otlp.jsonl \
    --card examples/agnostic_demo/agents/refill_bot/agent-card.json \
    --tools examples/agnostic_demo/agents/refill_bot/tools.json
```

## 6. Configuration

A YAML or JSON file passed with `--config` (or `AGENTEST_CONFIG`). Everything is optional.

```bash
cat > build/guide/agentest.yaml <<'YAML'
disable: [T7-004, X-005]        # reported as n/a ("disabled by config")
thresholds:
  steps: 20                     # budgets: steps, tokens, seconds, tool_calls, retries, burst
  success_rate: 0.8             # task-success SLO when the AgentCard publishes none
YAML
agentest std run --agents examples/agnostic_demo/agents --config build/guide/agentest.yaml --ids T7-004,X-001
```

Facts about **your** agent (who may approve, which tools are admin-only, tenancy, allowed hosts, approval TTLs,
compensating actions, data freshness and so on) belong in the AgentCard governance extension, not in the config.
See [EXTENSION.md](standards/EXTENSION.md).

## 7. Reading the outputs

Every verdict is `pass`, `fail`, `n/a` or `not-assessed`, with a `detail` that names the evidence (a tool call, an
argument, an output excerpt) or, for `n/a`, the missing signal. `n/a` is never counted as a pass.

`not-assessed` means the check needs a semantic judgement ("does this reply refuse?", "do these replies differ in
tone?") and no judge answer was available. Configure a judge (any OpenAI-compatible endpoint, for example a local
llama.cpp server) with `--judge`, or replay cached answers with `--judge-offline`. Without a judge, agentest never
falls back to keyword matching. See [JUDGE.md](standards/JUDGE.md).

```bash
agentest std run --agents examples/agnostic_demo/agents --judge off --ids T7-001,X-015
agentest std run --agents examples/agnostic_demo/agents --judge-offline --ids T7-001,X-015
```

**Bias (T7-007).** If the AgentCard skill `examples` contain a value of a protected attribute declared in governance
`fairness`, record one run per counterfactual variant. agentest generates the variants, `agentest std gen` lists them,
and each run's root span carries `agentest.input.counterfactual`. The check then confirms each variant differs from its
base only in the attribute. It compares decisions, structured output, tools, refusals, tone and reply length within
each group. It reports the flip rate against `maxFlipRate`, and the four-fifths ratio when a `favorable` outcome is
declared and each value has at least 3 runs.

```bash
agentest std run --agents examples/agnostic_demo/agents --format json  --out build/guide/verdicts.json
agentest std run --agents examples/agnostic_demo/agents --format junit --out build/guide/verdicts.xml
agentest std run --agents examples/agnostic_demo/agents --format sarif --out build/guide/verdicts.sarif
agentest std run --agents examples/agnostic_demo/agents --format html  --out build/guide/verdicts.html
agentest std run --agents examples/agnostic_demo/agents --emit-otlp build/guide/verdicts.otlp.json
```

| format | consumer | notes |
|:--|:--|:--|
| `json` | scripts, dashboards | versioned: [verdicts.schema.json](../src/agentest/standards/schemas/verdicts.schema.json) (`agentest.verdicts/1`) |
| `junit` | any CI test tab | one testcase per agent x ID; `fail` is a failure, `n/a` is skipped |
| `sarif` | code-scanning UIs | one result per `fail` |
| `html`, `md` | people | matrix plus details |
| `--emit-otlp` | your observability backend | one `agentest.run` span per agent, one `gen_ai.evaluation.result` event per ID, linked to the judged traces |

## 8. CI integration

Fail the build on any `fail`, and keep the JUnit report:

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot --strict --format junit --out build/guide/ci.xml
```

GitHub Actions (any CI with a Python step works the same way):

```yaml
- uses: actions/setup-python@v5
  with: { python-version: "3.12" }
- run: pip install "agentest @ git+https://github.com/srpadmanabhuni/agentest@v3.4.0"
- run: agentest std validate --agents agents
- run: agentest std run --agents agents --strict --format junit --out agentest.xml
- uses: actions/upload-artifact@v4
  if: always()
  with: { name: agentest, path: agentest.xml }
```

## 9. Per-test guides

- [docs/tests/](tests/README.md): one page per ID with the rule, the inputs it reads, how to run it and the
  current matrix over the bundled agents.
- [Per-test guide](testers/PER-TEST-GUIDE.md): purpose, pass/fail, triage and sources for all 130 IDs.
- [Coverage table](COVERAGE.md): how many bundled reference agents decide each ID (generated, checked in CI).
- [Triaging false positives](testers/FALSE-POSITIVES.md).

## 10. FAQ

**Do I need a model, an API key or network access?** No. Judging is deterministic and offline. Only recording new
traces of the bundled reference agents needs a local model.

**Why is a test `n/a` on my agent?** Its signal is missing: no run of the needed kind in the traces, or a fact that
is not declared (for example no tool marked `destructiveHint`). The `detail` says which. Add the trace or the
declaration; never edit the rule.

**Can I keep my own thresholds or rules?** Yes, with `--config` and `--rules-dir` or an installed plugin; no fork.

**Is anything tied to a vendor, a framework or a bundled agent?** No. `tests/test_agent_independence.py`,
`tests/test_no_lock_in.py` and the rename/mutation test fail the build if a rule names an agent or tool, if
per-agent profiles return, or if verdicts change when every agent and tool is renamed.

**Where did the v2 per-agent YAML profiles go?** Removed in v3.1.0. See the
[CHANGELOG](../CHANGELOG.md) migration note; the history stays at the `v2.0.0` tag.

**How do I report a wrong verdict?** Open an issue with the trace file, the AgentCard and the tools list
(or contact srinivas AT testAIng.com).
