# More from the README

The [README](../README.md) is now one 60-second path: install, `agentest demo`, then judge your own agent. The longer sections that used to follow it are kept here unchanged. The clone-based quickstarts moved to [Install and quickstart](INSTALL-AND-QUICKSTART.md).

## Tutorials

Seven short walkthroughs in this repository. Each one runs from the same clone as the quickstart (about 5–10 minutes).

| # | Tutorial | Checks |
|---|---|---|
| 1 | [Unauthorized tool calls](https://github.com/srpadmanabhuni/agentest/blob/main/docs/tutorials/01-unauthorized-tool-calls.md) | T5-001, T5-005 |
| 2 | [Prompt injection](https://github.com/srpadmanabhuni/agentest/blob/main/docs/tutorials/02-prompt-injection.md) | T4-001, T4-003, T4-007 |
| 3 | [State drift across turns](https://github.com/srpadmanabhuni/agentest/blob/main/docs/tutorials/03-state-drift.md) | T6-002, T6-003 |
| 4 | [CI/CD with GitHub Actions](https://github.com/srpadmanabhuni/agentest/blob/main/docs/tutorials/04-ci-cd-github-actions.md) | gated with `--strict` |
| 5 | [Multi-agent handoffs](https://github.com/srpadmanabhuni/agentest/blob/main/docs/tutorials/05-multi-agent-handoffs.md) | T3-001, T3-002, T3-007, T3-008, T3-010, T3-011 |
| 6 | [Personal data and secret leaks](https://github.com/srpadmanabhuni/agentest/blob/main/docs/tutorials/06-personal-data-leaks.md) | T5-004, T4-009, T6-011, T7-014 |
| 7 | [Writing expected outcomes for your own agent](https://github.com/srpadmanabhuni/agentest/blob/main/docs/tutorials/07-writing-expected-outcomes.md) | T1-001, T1-002, T1-018 |

Index: [docs/tutorials/README.md](https://github.com/srpadmanabhuni/agentest/blob/main/docs/tutorials/README.md).

**Agent Testing 101** on Substack ([publication](https://agenttesting101.substack.com)):

- [Build a Tiny AI Agent and Test It with agentest](https://agenttesting101.substack.com/p/build-a-tiny-ai-agent-and-test-it)
- [Test AI Agents for Unauthorized Tool Calls in 5 Minutes](https://agenttesting101.substack.com/p/test-ai-agents-for-unauthorized-tool)
- Launch note: [I'm launching agentest](https://agenttesting101.substack.com/p/im-launching-agentest)

Related article: [100 Days of Testing Agentic AI](https://srinivaspadmanabhuni.hashnode.dev/100-days-of-testing-agentic-ai-an-engineering-log-of-what-actually-breaks) on Hashnode.

## Now point it at your agent

```bash
# 1. Judge your agent's OpenTelemetry GenAI traces
agentest std run --otlp my_traces.otlp.jsonl

# 2. Optionally add its A2A AgentCard and MCP tools list for more checks
agentest std run --otlp my_traces.otlp.jsonl --card agent-card.json --tools tools.json

# 3. Gate CI (also json, sarif, html, md, csv)
agentest std run --otlp my_traces.otlp.jsonl --format junit --out agentest.xml --strict
```

No traces yet? [Emit one with the standard library](https://github.com/srpadmanabhuni/agentest/blob/main/examples/otel_plain/emit_trace.py), [import a native log](https://github.com/srpadmanabhuni/agentest/blob/main/docs/walkthroughs/05-bring-your-own-log.md), or [use LangGraph](https://github.com/srpadmanabhuni/agentest/blob/main/docs/integrations/langgraph.md) (run `python examples/langgraph_import/test_langgraph.py` for an offline example). A check with no evidence in your trace says `n/a`, never a silent `pass`.

Install from PyPI (https://pypi.org/project/agentest-ai/):

```bash
pip install agentest-ai
```

For the latest unreleased code:

```bash
pip install git+https://github.com/srpadmanabhuni/agentest
```

A git clone is only needed when you want the examples folder and bundled walkthroughs. More options: [install and quickstart](https://github.com/srpadmanabhuni/agentest/blob/main/docs/INSTALL-AND-QUICKSTART.md).

## Why agentest

agentest reads the traces your agent already recorded and tells you, check by check, what it did wrong: claimed success it did not earn, acted before verifying, followed an instruction hidden in a document, called a tool it should not, or leaked personal data. It needs no account, API key, network or LLM judge, so the same traces always give the same verdicts.

**Who it is for**

- **Agent developers:** catch broken tool calls, unearned "Done!" replies and prompt injection before your users do. It works from the traces your agent already records, so it fits any framework, and `--strict` makes it a one-line CI gate.
- **QA and testers:** 165 tests with deterministic `pass` / `fail` / `n/a` verdicts and an evidence line each. No LLM judge, so no flaky scores. It reads OpenTelemetry GenAI traces, A2A AgentCards and MCP tool lists.

**What makes it different** ([every point, with its source](https://github.com/srpadmanabhuni/agentest/blob/main/docs/START_HERE.md#what-makes-agentest-different)):

- **One open suite of 165 tests** spanning evals, security, privacy and responsible behaviour.
- **Judges what your agent did** (tool calls and results), not only what it said.
- **Deterministic and offline:** no LLM judge, API key or network.
- **Open standards, no lock-in:** reads OpenTelemetry GenAI, A2A AgentCard and MCP tool annotations from any framework, and never asks your agent to import it ([No lock-in](https://github.com/srpadmanabhuni/agentest/blob/main/docs/NO-LOCK-IN.md), [agent-independence audit](https://github.com/srpadmanabhuni/agentest/blob/main/docs/standards/AGENT-INDEPENDENCE-AUDIT.md)).
- **Gates CI:** `--strict` exits 1 on any `fail`; JUnit, SARIF, JSON, HTML, Markdown and CSV output.

Use it for a [pre-release gate, regression checks after a prompt change, security review, or evaluating another team's agent](https://github.com/srpadmanabhuni/agentest/blob/main/docs/START_HERE.md#use-it-for). Limits, known false positives and coverage are in [How it works](https://github.com/srpadmanabhuni/agentest/blob/main/docs/HOW-IT-WORKS.md). Not certification.

**Your move:** [try the quickstart](#quickstart), take the [challenge: can your agent pass these tests?](https://github.com/srpadmanabhuni/agentest/blob/main/docs/CHALLENGE.md); or open a [good first issue](https://github.com/srpadmanabhuni/agentest/labels/good%20first%20issue).

## Choose your path

| I am... | Start with |
|---|---|
| **A developer** (install, first run, CI, CLI and API, contributing) | [Start here](https://github.com/srpadmanabhuni/agentest/blob/main/docs/START_HERE.md#the-path) · [Quickstart](#quickstart) · [Tutorials](#tutorials) · [Point it at your agent](#now-point-it-at-your-agent) · [CI gate](https://github.com/srpadmanabhuni/agentest/blob/main/docs/developers/CI.md) · [CLI and API reference](https://github.com/srpadmanabhuni/agentest/blob/main/docs/developers/REFERENCE.md) · [Contribute](#contribute) |
| **A tester / QA** (what each test checks, manual use, packs, priorities, reading verdicts) | [Tester quickstart](https://github.com/srpadmanabhuni/agentest/blob/main/docs/testers/QUICKSTART.md) · [Per-test guide](https://github.com/srpadmanabhuni/agentest/blob/main/docs/testers/PER-TEST-GUIDE.md) · [Plan by priority](https://github.com/srpadmanabhuni/agentest/blob/main/docs/testers/TEST-PLANNING.md) · [Read a verdict](#read-a-verdict-pass-fail-na) · [Use the checklist by hand](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110#use-this-checklist-without-agentest) |
| **New to agent testing** | [Start here](https://github.com/srpadmanabhuni/agentest/blob/main/docs/START_HERE.md#the-path): install, run the demo, then judge your own trace. |

> **Launched 15 Nov 2026.** Install from PyPI and try it in under 3 minutes. Then take the [challenge](https://github.com/srpadmanabhuni/agentest/blob/main/docs/CHALLENGE.md), or open a [good first issue](https://github.com/srpadmanabhuni/agentest/labels/good%20first%20issue).


## Where things live

This repository is the front door. The other public repos and Spaces are companions; start here, then follow the link you need.

| Resource | What it is for |
|---|---|
| [agentest](https://github.com/srpadmanabhuni/agentest) (this repository) | The runner: install it, run the checks, read the report, and contribute. Package name `agentest-ai`; import and CLI `agentest`. |
| [agentest-starter](https://github.com/srpadmanabhuni/agentest-starter) | A template that runs agentest on a sample agent, then on your own recorded traces. |
| [Reference agents](https://huggingface.co/srinivaspadmanabhuni/agentic-ai-reference-agents) | 132 practice agents with recorded runs, on Hugging Face. This repository bundles 98 of those reference agents plus 15 samples (113 directories in `agents/`). |
| [Agentic AI Test Checklist 110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) | The open catalogue of 110 test designs (objectives, pass/fail signals). |
| [Assurance Report Card](https://huggingface.co/spaces/srinivaspadmanabhuni/agentest-assurance-report-card) | Paste or upload a trace in the browser and see which checks fail; no install. |
| [Checklist browser](https://huggingface.co/spaces/srinivaspadmanabhuni/agentic-ai-test-checklist-demo) | Filter and export the 110 tests in the browser. |
| [Reference-agents viewer](https://huggingface.co/spaces/srinivaspadmanabhuni/agentic-ai-reference-agents-viewer) | Read the recorded runs of the reference agents. |

## How agentest compares

The table contrasts agentest with two generic approaches: LLM-as-a-judge evaluation tools, and cloud observability platforms. It describes evaluation mode; it is not a ranking. A longer page is [How agentest compares](https://github.com/srpadmanabhuni/agentest/blob/main/docs/HOW-AGENTEST-COMPARES.md).

| Dimension | agentest | LLM-as-a-judge evaluation tools | Cloud observability platforms |
|---|---|---|---|
| Execution mode | Offline and deterministic. The same traces produce the same verdicts. No model is called at evaluation time. | Typically depend on a model, and often on a network, to score outputs. Verdicts can vary between runs. | Typically require a hosted account and ingested telemetry. |
| Evaluation target | Execution traces, tool-call order, state changes, and declared tool or agent metadata. | Often the final text: similarity, hallucination, or other output-quality scores. | Often monitoring, debugging and trace inspection. Evaluation, when present, is a separate feature. |
| Cost and latency | No model or API token cost at evaluation time. Runtime is local rule checks over the recorded trace. | Incur model token cost and added latency for each scored trace. | Incur platform usage costs. Latency depends on the hosted pipeline. |
| Standards and inputs | Reads OpenTelemetry GenAI traces, A2A AgentCards and MCP tool lists. | Vary by product. Inputs are often prompt and output pairs rather than tool-level traces. | Often traces and metrics. They do not necessarily read A2A AgentCards or MCP tool lists. |

## Extension packs (opt-in, outside the 165 tests)

The 165 tests are unchanged, and the default `agentest std run` output is unchanged; a test asserts it. Extra areas ship as separate packs with their own prefixes. You select them with `--pack` or `--ids`; they never enter the default run.

| Pack | Checks | Covers |
|---|---:|---|
| `ma` | 13 | multi-agent: attribution, delegation graph, handoff fidelity, loops, conflicts, failure containment |
| `pv` | 8 | privacy: health identifiers, minimisation, consent withdrawal, cross-session leakage, erasure, secrets |
| `rt` | 6 | red-teaming: jailbreaks, multi-turn refusal bypass, look-alike and poisoned tools, prompt extraction |
| `bf` | 5 | bias and fairness: counterfactual pairs, group refusal gaps |
| `ex` | 5 | explainability: what the agent says matches the trace |
| `dl` | 4 | data lineage: provenance of written values, data-class downflow |
| `rai` | 5 | the five responsible-AI additions (`T1-020`, `T1-021`, `T3-018`, `T3-019`, `T7-017`) |

```bash
agentest list --packs
agentest std run --agents examples/multi_agent --agent triage_team_seeded --pack ma
```

Same rules as the core set: offline, deterministic, no model, no per-agent adapter; missing attributes give n/a, never a fail. Details: [Extension packs](packs/README.md), with a page per pack and reference multi-agent agents in [`examples/multi_agent/`](../examples/multi_agent/).

## Roadmap

Open source, in this repository. The [full roadmap](https://github.com/srpadmanabhuni/agentest/blob/main/docs/ROADMAP.md) has the detail; it is a plan, not a commitment. The pinned pointer is [issue #272](https://github.com/srpadmanabhuni/agentest/issues/272). Suggestions: [Discussion #80](https://github.com/srpadmanabhuni/agentest/discussions/80).

- [x] Rule engine with 165 tests, deterministic and offline
- [x] The 110-test checklist dataset on [Hugging Face](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110)
- [x] Validation method: blind, label-locked evaluation ([how it works](https://github.com/srpadmanabhuni/agentest/blob/main/docs/HOW-IT-WORKS.md))
- [x] CI gate (`--strict`, JUnit and SARIF output) and a no-install Colab and browser demo
- [x] LangGraph importer and a worked example
- [ ] Deeper framework adapters beyond the existing native-log importers (LangGraph, OpenAI Agents SDK, AutoGen, smolagents and n8n)
- [ ] Extension packs: multi-agent, privacy, red teaming, bias, explainability and data lineage
- [x] PyPI release of `agentest-ai` (3.5.0, https://pypi.org/project/agentest-ai/)

Want to build one? See [Contribute](#contribute), including [Help own a check family](#help-own-a-check-family).

## Seen in

agentest is listed in [awesome-testing](https://github.com/TheJambo/awesome-testing), [awesome-ai-eval](https://github.com/Vvkmnn/awesome-ai-eval) and [Awesome-AI-Agents](https://github.com/Jenqyang/Awesome-AI-Agents).

The open [test checklist](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) on Hugging Face is also listed in [awesome-llm-security](https://github.com/beyefendi/awesome-llm-security) and [awesome-ai-governance](https://github.com/agentrust-io/awesome-ai-governance).

A [course notebook](https://github.com/srpadmanabhuni/agentest/blob/main/examples/course/agent_testing_course.ipynb) walks a class or team through planning tests with the checklist and filling them with agentest verdicts ([open in Colab](https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/examples/course/agent_testing_course.ipynb)).

## Frequently asked questions

### How do I evaluate LangGraph or CrewAI agents offline without an LLM judge?

agentest judges recorded traces with deterministic rules. It does not call a model. For LangGraph, emit OpenTelemetry GenAI spans, or convert a recorded message list with `agentest std import` and the `langgraph_msgs` dialect, then run `agentest std run`. See [LangGraph](https://github.com/srpadmanabhuni/agentest/blob/main/docs/integrations/langgraph.md). For CrewAI there is no built-in CrewAI import dialect yet: export OpenTelemetry GenAI traces, or import a task list with the `steps` dialect or a `file:` adapter. See [CrewAI](https://github.com/srpadmanabhuni/agentest/blob/main/docs/integrations/crewai.md).

### What is the difference between agentest-ai on PyPI and agentest?

`agentest-ai` is the package name on PyPI. The import and the CLI are `agentest`. The name `agentest` on PyPI belongs to a different project.

```bash
pip install agentest-ai
```

```bash
python -c "import agentest"
agentest --help
```

### How do I gate a GitHub Actions CI/CD pipeline on AI agent trace failures?

Install the package, judge your traces, and pass `--strict` so the job exits with status 1 when any check fails:

```bash
pip install agentest-ai
agentest std run --otlp traces.otlp.jsonl --format junit --out agentest.xml --strict
```

`--format sarif` is available for code scanning. A walkthrough is [CI/CD with GitHub Actions](https://github.com/srpadmanabhuni/agentest/blob/main/docs/tutorials/04-ci-cd-github-actions.md). An example workflow is [`examples/integrations/github-actions-gate.yml`](https://github.com/srpadmanabhuni/agentest/blob/main/examples/integrations/github-actions-gate.yml).

### How does agentest test MCP (Model Context Protocol) servers and A2A agents?

agentest does not start or host an MCP server. Pass the MCP `tools/list` JSON with `--tools` and the A2A AgentCard with `--card`. Checks read tool names, schemas and annotations together with the recorded OpenTelemetry GenAI `execute_tool` spans:

```bash
agentest std run --otlp traces.otlp.jsonl --card agent-card.json --tools tools.json
```

`--card` and `--tools` are optional; checks that need a declared fact report `n/a` when that file is missing.

### Does agentest need an API key or a model to judge a trace?

No. Judging is offline and deterministic. The only required runtime dependency is PyYAML. No account, API key, network or model is used to produce `pass`, `fail` or `n/a`.

### When should I not use agentest?

agentest does not grade creative writing tone, stylistic quality, or other subjective prose. See [How agentest compares](https://github.com/srpadmanabhuni/agentest/blob/main/docs/HOW-AGENTEST-COMPARES.md) and [When not to use agentest](#when-not-to-use-agentest).

More short answers are in the [FAQ](https://github.com/srpadmanabhuni/agentest/blob/main/docs/FAQ.md).

## Help own a check family

We are looking for co-maintainers, one per area:

- **Extension families:** red teaming, privacy, bias, explainability, data lineage and multi-agent.
- **Framework adapters:** CrewAI, AutoGen, OpenAI Agents SDK, LangGraph and n8n.

To volunteer, comment on the [contributor week Discussion](https://github.com/srpadmanabhuni/agentest/discussions/100). What an owner does is in [CONTRIBUTING.md](https://github.com/srpadmanabhuni/agentest/blob/main/CONTRIBUTING.md#help-own-a-check-family).
