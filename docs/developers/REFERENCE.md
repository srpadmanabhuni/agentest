# API and CLI reference

## CLI: `agentest std`

```
agentest std {validate,run,regress,export,gen,catalog} [options]
```

| Action | What it does |
|---|---|
| `validate` | checks each agent folder's AgentCard and MCP tools structure; exit 1 if any is invalid |
| `run` | evaluates all 136 IDs for each agent; prints a summary, or a report with `--format` |
| `regress` | compares verdicts with the v2 baseline (`fixtures/standards/v2-baseline.json`); the catch table |
| `export` | writes each agent's runs as OTLP/JSON (`--out`, default `otlp/`) |
| `gen` | prints generated test inputs from the card and tool schemas |
| `catalog` | prints the catalogue as JSON or `--format csv` |

| Option | Meaning |
|---|---|
| `--agents DIR` | folder of agent folders (default: bundled `agents/`) |
| `--agent ID` | only this folder |
| `--mode strict\|examples` | see [concepts](CONCEPTS.md#two-modes); default `examples` |
| `--format json\|junit\|sarif\|md\|html\|csv` | report format; written to `--out`, or stdout if `--out` is absent |
| `--out PATH` | output file (or directory for `export`) |
| `--json PATH` | `run`/`regress`: raw JSON results |
| `--strict` | `run`: exit 1 if any ID fails |
| `--otlp FILE...` | judge plain OTLP/JSON files, no agent folder needed |
| `--card FILE`, `--tools FILE` | with `--otlp`: optional AgentCard and MCP tools/list |
| `--config FILE` | YAML/JSON config (also `AGENTEST_CONFIG`) |
| `--rules-dir DIR` | import extra rule modules (also `AGENTEST_RULES_DIR`) |

The only other top-level commands are `agentest list` (catalogue IDs) and `agentest version`. The v1/v2 commands
(`agentest run`, `real`, `check`, `matrix`, `samples`, `model`) were removed in v3.1.0; their history is at the `v1.0.0`
and `v2.0.0` tags, and the [CHANGELOG](../../CHANGELOG.md) has the migration note.

## Config file

```yaml
disable: [T7-004, X-005]     # reported as n/a ("disabled by config")
thresholds:                  # steps, tokens, seconds, tool_calls, retries, burst, success_rate
  steps: 20
  success_rate: 0.8
rules_dir: my_rules/         # extra @rule modules
scenarios: my_scenarios.yaml # extra conformance oracles (same format as scenarios.yaml)
```

Governance `limits` published by an agent take precedence over these defaults.

## Output schemas

| Format | Schema | Notes |
|---|---|---|
| `json` | [`agentest.verdicts/1`](../../src/agentest/standards/schemas/verdicts.schema.json) | versioned; a breaking change bumps `/1` |
| `sarif` | OASIS SARIF 2.1.0 | one result per fail; rules carry the catalogue title |
| `junit` | JUnit XML | fail = `<failure>`, n/a = `<skipped>` |
| `md`, `html` | human-readable tables | |
| `csv` | `agent,id,status,detail` | |

## Python API

```python
from pathlib import Path
from agentest.standards import metadata, runner, rules, reports, otel, ext

agents = metadata.load_all(Path("agents"))             # {folder_id: Agent}
a = agents["my_agent"]
runs = runner.runs(a)                                  # list[otel.Run] from OTLP or adapters
verdicts = rules.evaluate(a, runs, mode="strict")      # {ID: R(status, detail)}
doc = reports.to_versioned_json(runner.to_json({"my_agent": verdicts}), "strict")

docs = otel.read_otlp_file("traces.jsonl")             # OTLP documents, one per trace
run = otel.from_otlp(docs[0])                          # a Run: input, answer, tools, approvals, effects, ...

ext.configure(ext.read_config("agentest.yaml"))        # thresholds, disable list, plugins
```

`Run` fields: `input_id`, `rep`, `input`, `answer`, `tools` (`ToolSpan`: `name`, `args`, `result`, `error`,
`actor`), `approvals`, `handoffs`, `effects`, `chats`, `final_state`, `error`, `duration_s`, `evaluations`.
