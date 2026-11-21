# agentest FAQ

New here? Start with [Getting started](GETTING-STARTED.md). Short answers with pointers into the [User Guide](USER-GUIDE.md) and [Author Guide](AUTHOR-GUIDE.md). Everything here
describes the code on `main` (version 3.5.1) unless it says otherwise. Every command below was run against `main`.


## What are agentic evals?

**Agentic evals are tests of an AI agent's actual behaviour — the tools it called, the order it called them, and the state it left behind — rather than only the text it produced.** agentest is an open-source tool for agentic evals: it runs 165 tests over recorded OpenTelemetry traces, offline and without an LLM judge. Install from PyPI (command in [Install](#install) below). A longer, citable page is [What are agentic evals?](what-are-agentic-evals.md).


## Frequently asked questions

These questions match the wording people (and AI engines) often use. Short answers; the sections below go into more detail.

### How do I evaluate LangGraph or CrewAI agents offline without an LLM judge?

agentest judges recorded traces with deterministic rules. It does not call a model.

For LangGraph, either emit OpenTelemetry GenAI spans from the run, or convert a recorded LangGraph / LangChain message list with `agentest std import` and the `langgraph_msgs` dialect, then run `agentest std run --otlp traces.otlp.jsonl`. A worked page is [LangGraph](integrations/langgraph.md).

For CrewAI there is no built-in CrewAI import dialect yet. Export OpenTelemetry GenAI traces from the crew, or dump each task's tool calls and import them with the built-in `steps` dialect or a small `file:` adapter, then run the same `agentest std run` command. Details: [CrewAI](integrations/crewai.md).

### What is the difference between agentest-ai on PyPI and agentest?

`agentest-ai` is the package name on PyPI. The import and the command-line entry point are both `agentest`:

```bash
pip install agentest-ai
```

```bash
python -c "import agentest"
agentest --help
```

The name `agentest` on PyPI belongs to a different project, which is why this package is published as `agentest-ai`.

### How do I gate a GitHub Actions CI/CD pipeline on AI agent trace failures?

Run agentest in the workflow and pass `--strict` so the job exits with status 1 when any check fails:

```bash
pip install agentest-ai
agentest std run --otlp traces.otlp.jsonl --format junit --out agentest.xml --strict
```

`--format junit` writes a report you can upload as a job artifact. `--format sarif` is available for code scanning. A worked walkthrough is [CI/CD with GitHub Actions](tutorials/04-ci-cd-github-actions.md). An example workflow is [`examples/integrations/github-actions-gate.yml`](../examples/integrations/github-actions-gate.yml). The repository also ships a GitHub Action (`action.yml`); see [GitHub Action](developers/GITHUB-ACTION.md).

### How does agentest test MCP (Model Context Protocol) servers and A2A agents?

agentest does not start or host an MCP server. It judges what an agent did with MCP tools and A2A metadata you already recorded.

Save the server's MCP `tools/list` result as JSON and pass it with `--tools`. Save the A2A AgentCard and pass it with `--card`. Checks read tool names, input schemas and annotations such as `readOnlyHint` and `destructiveHint`, plus AgentCard fields, together with the OpenTelemetry GenAI `execute_tool` spans from the run:

```bash
agentest std run --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json
```

`--card` and `--tools` are optional; checks that need a declared fact report `n/a` when that file is missing. See [Writing the AgentCard](developers/AGENT-CARD.md) and [Instrumenting your agent](developers/INSTRUMENTING.md).

### Does agentest need an API key or a model to judge a trace?

No. Judging is offline and deterministic. The only required runtime dependency is PyYAML. No account, API key, network or model is used to produce `pass`, `fail` or `n/a`.

### When should I not use agentest?

agentest does not grade creative writing tone, stylistic quality, or other subjective prose. It is not a model leaderboard, and a passing run is not certification. See [How agentest compares](HOW-AGENTEST-COMPARES.md).

## Install

**How do I install it?**

```bash
pip install agentest-ai
# pin a release: pip install "agentest-ai==3.5.1"
# or from git: pip install "agentest-ai @ git+https://github.com/srpadmanabhuni/agentest.git@v3.5.2"
agentest version          # 3.5.1
```

From a clone (needed for the `examples/` folder used below):

```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
```

**What does it depend on?** Python 3.11+ and PyYAML. No account, API key, network or model is needed to judge.
Optional extras: `agentest-ai[otlp]` (official OTLP/protobuf decoder) and `agentest-ai[dev]` (pytest, ruff, jsonschema).

**Is it on PyPI?** Yes: `pip install agentest-ai` ([PyPI page](https://pypi.org/project/agentest-ai/)). The import name and
the `agentest` command stay `agentest`.

**Does agentest run my agent or call a model?** No. It reads what your agent already recorded (traces, and optionally
its AgentCard and MCP tools list) and judges it with deterministic rules. Nothing is sent anywhere.

## Quickstart

**What is the fastest way to see it work?** From a clone:

```bash
agentest std validate --agents examples/agnostic_demo/agents
agentest std run --agents examples/agnostic_demo/agents
# refill_bot: 55 pass, 0 fail; refill_bot_buggy: 41 pass, 16 fail
```

The same demo is in [examples/colab_quickstart.ipynb](../examples/colab_quickstart.ipynb) (free CPU, no login, no model). GitHub renders that file; a separate docs site is not required.

**How do I run it on my own agent?** Give it an OTLP trace file; the A2A AgentCard and MCP tools list are optional:

```bash
agentest std run --otlp my_traces.otlp.jsonl --card agent-card.json --tools tools.json
```

To see the expected trace shape, generate one with the standard library only:

```bash
mkdir -p build
python examples/otel_plain/emit_trace.py > build/trace.otlp.json
agentest std run --otlp build/trace.otlp.json \
    --card examples/otel_plain/agent-card.json --tools examples/otel_plain/tools.json
```

**How do I use it in CI?**

```bash
agentest std run --format junit --out agentest.xml --strict
```

`--strict` exits with status 1 if any verdict is `fail`. Other formats: `json`, `sarif`, `md`, `html`, `csv`.
Use `--ids T1-001,T6-010` to limit the report to some checks, and `--config` to disable IDs or set thresholds
([User Guide §6](USER-GUIDE.md#6-configuration)).

## The catalogue

**How many tests does agentest ship?** 165 tests. The published catalogue is the [Agentic AI Test Checklist 110](../README.md#what-it-checks).

**What are the classes T1–T7?** List them with `agentest list`, or one class with `agentest list --class T3`. List class X with `agentest list --class X`.
The catalogue file ships in the package (`catalog/checklist-110.jsonl`) with the class, eval group, objective and
severity of each test.

**Can I filter the list by severity or eval group?** Yes. Use `--severity` and `--group` (comma-separated, case-insensitive). They combine with `--class`. Example: `agentest list --severity critical --group security`. `agentest list --json` still includes severity and group for further filtering.

**How do the tests map to standards?** Per-ID mappings to OWASP LLM Top 10 2025, OWASP Agentic, NIST AI RMF / 600-1,
ISO/IEC 42001 Annex A and MITRE ATLAS are in [STANDARDS-MAP.md](standards/STANDARDS-MAP.md). The class-level crosswalk
in [FRAMEWORK-MAPPING.md](FRAMEWORK-MAPPING.md) is indicative; corrections with sources are welcome (issue #5).

**How do I cite it?** Use [CITATION.cff](../CITATION.cff) (GitHub shows a "Cite this repository" button). The
checklist dataset also has a Zenodo all-versions DOI, listed there.

## Agent-agnostic usage

**Does it only work with a particular framework?** No. Every check is one universal rule over standard artifacts:
OpenTelemetry GenAI spans, the A2A AgentCard and MCP tool annotations. No rule names an agent, a tool or a vendor,
and CI enforces this with the [agent-independence audit](standards/AGENT-INDEPENDENCE-AUDIT.md) and the
[no-lock-in checks](NO-LOCK-IN.md).

**My agent already emits OpenTelemetry.** Export the spans to a file with any OTLP file exporter, or point an
OTLP/HTTP exporter at the built-in collector:

```bash
agentest std serve --out build/inbox --port 4319 --max-requests 1
```

**My agent is not instrumented.** Convert its native log once with `agentest std import`. Built-in dialects on
`main`: `steps`, `events`, `openai_agents` (OpenAI Agents SDK run items), `langgraph_msgs` (LangGraph message
lists), `autogen`, `smolagents` (smolagents memory steps) and `n8n`. Anything else uses a JSON mapping file or a `file:my.py` adapter
([Author Guide §3](AUTHOR-GUIDE.md#3-a-framework-adapter)).

```bash
agentest std import examples/agnostic_demo/native/refill_bot.jsonl \
    --map examples/agnostic_demo/import/map.json \
    --tools examples/agnostic_demo/agents/refill_bot/tools.json \
    --service refill_bot --out build/refill_bot.otlp.jsonl
agentest std run --otlp build/refill_bot.otlp.jsonl \
    --card examples/agnostic_demo/agents/refill_bot/agent-card.json \
    --tools examples/agnostic_demo/agents/refill_bot/tools.json
```

A LangGraph example is in `examples/langgraph_import/` (`python examples/langgraph_import/test_langgraph.py`). Instrumentation guide: [integrations/langgraph.md](integrations/langgraph.md). A smolagents example is in `examples/smolagents_import/`.

**Is there a CrewAI, AutoGen, LangGraph or OpenAI Agents SDK example?** Built-in import dialects already cover
AutoGen (`autogen`), LangGraph message lists (`langgraph_msgs`) and OpenAI Agents SDK run items (`openai_agents`);
`examples/langgraph_import/` shows one end to end. There is no CrewAI dialect yet: export its tool calls to JSON and
use a mapping file or a `file:my.py` adapter. Worked pages that judge real recorded runs: [CrewAI](integrations/crewai.md) and
[OpenAI Agents SDK](integrations/openai-agents-sdk.md). Runnable live-export examples for each framework are open
"good first issues" (#1–#4); contributions are welcome.

**Are there Python converters for LangGraph state or the OpenAI Agents SDK?** Not on `main` yet. Richer converters
(LangGraph state and checkpoint history, OpenAI Agents SDK `new_items`) and an `agentest std lint` command are in
review and not released. On `main`, use `agentest std import` with the dialects above.

## Verdicts

For a beginner-friendly walk-through of a report, including the four formats and how to read
a verdict's `detail` line, see [Reading the report](READING-THE-REPORT.md). The short answers
are below.

**What do `pass`, `fail` and `n/a` mean?**

| Verdict | Meaning |
|---|---|
| `pass` | The rule found the signal it needs and the behaviour met the rule. |
| `fail` | The rule found the signal and the behaviour broke the rule. `detail` names the evidence (tool call, argument, output excerpt). |
| `n/a` | The signal the rule needs is missing, or the ID was disabled by config. `detail` names what is missing. |

`n/a` is **never** counted as a pass. In JUnit it is reported as skipped.

**Why are so many of my checks `n/a`?** Usually the rule needs a fact your traces or card do not carry yet: for example
which tools change state (MCP `readOnlyHint`/`destructiveHint`), the expected outcome, the user's language, or
approval records. Add the span attribute or publish the fact, and the check becomes a real `pass`/`fail`. See
[User Guide](USER-GUIDE.md) and the [governance extension](standards/EXTENSION.md).

**What are `strict` and `examples` modes?** `strict` reads only standard fields and the extension. `examples` (the
default) also uses the success criteria published in the AgentCard skill examples.

## Scoring and metrics

**Is there one overall score?** No. agentest reports a verdict per agent × check, plus totals of pass, fail and
n/a. It is not a leaderboard.

**How do you measure agentest's own accuracy?** With blind rounds: agents with planted defects whose answer key is
sealed until the rules are frozen ([BLIND-TEST.md](BLIND-TEST.md)). We report:
- **precision**: of the defects agentest flags, how many are real;
- **recall**: of the planted defects, how many agentest flags;
- **control false alarms**: failures on clean control agents (target 0).

Accuracy work is in progress. We will publish numbers only after they have been verified across blind rounds.

## Known limits

- **High `n/a` without signals.** Many checks stay `n/a` until the agent emits the needed attributes.
- **Accuracy is still being improved.** Some rules miss real defects or raise false alarms. Please report them
  using the false-positive and false-negative issue forms.
- **Heuristics on free text.** Several rules use English regex heuristics (claims, warnings, refusals). They are
  deterministic but uncalibrated; see [false positives](testers/FALSE-POSITIVES.md).
- **Reference agents run on a small local model** with a few runs per input.
- **Not certification.** The checklist is informed by ISO 42001 themes, but a run is not an audit.
- No model judge sits in the pass/fail path.

## Contributing and support

- How to contribute: [CONTRIBUTING.md](../CONTRIBUTING.md). New checks follow the [Author Guide](AUTHOR-GUIDE.md).
- Bugs, feature requests and wrong verdicts: open a GitHub issue using the matching form.
- Questions: [SUPPORT.md](../SUPPORT.md).
- Security issues: email srinivas AT testAIng.com instead of opening a public issue.
- **Never paste secrets, API keys or personal data in an issue.** Redact traces first.
