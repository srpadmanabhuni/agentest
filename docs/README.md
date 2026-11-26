# Documentation index

agentest (agentest-ai on PyPI) is an open-source, offline, deterministic evaluation framework for AI agents. Built by Dr. Srinivas Padmanabhuni (AiEnsured), it checks OpenTelemetry GenAI traces, A2A AgentCards and MCP tool lists against 165 rule-based tests, catching unauthorized tool calls, prompt injections, unearned success claims and PII leaks without an LLM judge.

**Choose your path**

| I am... | Start with |
|---|---|
| A developer | [Quickstart](QUICKSTART.md) · [Tutorials](#tutorials) · [Getting started](GETTING-STARTED.md) · [CI integration](developers/CI.md) · [GitHub Action](developers/GITHUB-ACTION.md) · [CLI and API reference](developers/REFERENCE.md) · [all developer docs](#developers-track-author-guide-then-these) |
| A tester / QA | [Quickstart](QUICKSTART.md) · [Tester quickstart](testers/QUICKSTART.md) · [Per-test guide](testers/PER-TEST-GUIDE.md) · [Reading the report](READING-THE-REPORT.md) · [New tests NT-001–NT-030](new-tests/README.md) · [all tester docs](#testers-track-user-guide-then-these) |

Questions? [Chat with us on Discord](https://discord.gg/7mnsWRGt5N) in the #help and #contributors channels.

## Start here

* [**Start here**](START_HERE.md#the-path): install, run the demo, judge your own trace, then [Use from Python](START_HERE.md#use-from-python). Other pages link back here.
* [**Quickstart**](QUICKSTART.md): the shopping-agent check on that same install (`agentest std run --agent a22 --ids T1-018 --format md`).
* [Getting started](GETTING-STARTED.md): install to first report and CI gate in six runnable steps.
* [Install and quickstart, all the ways](INSTALL-AND-QUICKSTART.md).
* [Reading the report](READING-THE-REPORT.md): `pass`, `fail` and `n/a`, verdict `detail` lines, the Trials section (`pass@k` and `pass^k`), and the four report formats.
* [FAQ](FAQ.md): short answers on install, your own agent, verdicts, known limits and support.
* [How agentest compares](HOW-AGENTEST-COMPARES.md): execution mode, evaluation target, cost and latency, standards, and when not to use agentest.
* [What are agentic evals?](what-are-agentic-evals.md): a short, citable definition, why they differ from output-only tests, and how to run them with agentest.

## Tutorials

Seven short walkthroughs. Each runs from the same repository clone as the [Quickstart](QUICKSTART.md).

1. [Unauthorized tool calls](tutorials/01-unauthorized-tool-calls.md) (T5-001, T5-005)
2. [Prompt injection](tutorials/02-prompt-injection.md) (T4-001, T4-003, T4-007)
3. [State drift across turns](tutorials/03-state-drift.md) (T6-002, T6-003)
4. [CI/CD with GitHub Actions](tutorials/04-ci-cd-github-actions.md)
5. [Multi-agent handoffs](tutorials/05-multi-agent-handoffs.md)
6. [Personal data and secret leaks](tutorials/06-personal-data-leaks.md)
7. [Writing expected outcomes for your own agent](tutorials/07-writing-expected-outcomes.md) (T1-001, T1-002, T1-018)

Index: [tutorials/README.md](tutorials/README.md). Also on Substack, [Agent Testing 101](https://agenttesting101.substack.com): [Build a Tiny AI Agent and Test It](https://agenttesting101.substack.com/p/build-a-tiny-ai-agent-and-test-it), [Unauthorized tool calls](https://agenttesting101.substack.com/p/test-ai-agents-for-unauthorized-tool). Related: [100 Days of Testing Agentic AI](https://srinivaspadmanabhuni.hashnode.dev/100-days-of-testing-agentic-ai-an-engineering-log-of-what-actually-breaks) (Hashnode).

## Concepts

* [What are agentic evals?](what-are-agentic-evals.md).
* [AI evaluation glossary](guides/EVAL-GLOSSARY.md): definitions of common eval terms and how each maps to agentest.
* [Concepts](developers/CONCEPTS.md): how traces, checks and verdicts fit together.
* [How it works, coverage and non-goals](HOW-IT-WORKS.md).
* [Why agentest matters for testers](guides/WHY-AGENTEST-FOR-TESTERS.md) and [for developers](guides/WHY-AGENTEST-FOR-DEVELOPERS.md).
* [Capability suites and regression suites](guides/CAPABILITY-AND-REGRESSION-SUITES.md), with [templates/regression.yaml](../templates/regression.yaml) and [templates/capability.yaml](../templates/capability.yaml).
* [No lock-in](NO-LOCK-IN.md): what is guaranteed and what the residual risks are.
* [Overlaps and gaps](OVERLAPS-AND-GAPS.md): how agentest relates to categories of evaluation tooling.

## Checks reference

* [Per-test guide](testers/PER-TEST-GUIDE.md) and the [per-ID test pages](tests/README.md).
* [New tests](new-tests/README.md): opt-in checks `NT-001` to `NT-030`. List with `agentest list --new-tests` and run with `agentest std run --ids NT` (that selection also includes T1-020 and T1-021).
* [Article-test coverage](ARTICLE-TEST-COVERAGE.md): how the default checks and the New tests map to The original 110 tests.
* [User Guide](USER-GUIDE.md): CLI, config, outputs and CI.
* [Catalogue and Hugging Face](CATALOGUE-AND-HF.md) and [How agentest relates to the Hugging Face checklist](CHECKLIST-AND-AGENTEST.md).
* [Responsible Agentic AI Testing Framework v0.1](FRAMEWORK.md): the 110 tests in four pillars with control coverage ([JSON](coverage-map.json); generated, checked in CI).
* [Coverage on the reference agents](COVERAGE.md) (generated, checked in CI).

## Adapters

Short Python examples that export a run and judge it: [LangChain / LangGraph](integrations/langgraph-record.md), [OpenAI Agents SDK](integrations/openai-agents-sdk-record.md), [Pydantic AI](integrations/pydantic-ai.md). Each is offline, no API key.

Test with pytest: [the agentest pytest plugin](integrations/pytest.md) asserts that a trace passes the checks you name and prints the failing check with its evidence.

* [LangGraph](integrations/langgraph.md), [LlamaIndex](integrations/llamaindex.md), [CrewAI](integrations/crewai.md), [OpenAI Agents SDK](integrations/openai-agents-sdk.md), [AutoGen](integrations/autogen.md), [smolagents](integrations/smolagents.md), [Agno](integrations/agno.md), [Vercel AI SDK](integrations/ai-sdk.md), [Google ADK](integrations/google-adk.md), [n8n](integrations/n8n.md), [MCP](integrations/mcp.md), and [adapters wanted](integrations/ADAPTERS-WANTED.md).
* [OpenTelemetry GenAI compatibility matrix](integrations/otel-genai-compatibility.md): which attributes, spans and events of the GenAI semantic conventions agentest reads, pinned to a commit (generated, checked in CI).
* [Author Guide](AUTHOR-GUIDE.md#3-a-framework-adapter): writing a `file:my.py` adapter.

## Guides and tutorials

* [**56-second demo with voiceover**](assets/agentest-demo-empty-cart.mp4): a shopping agent says "added to the cart", its trace has no add_to_cart call, and T1-018 fails. Reproduce it with `agentest std run --agent a22 --ids T1-018 --format md`.
* [Bug-detection demo](demos/BUG-DETECTION-DEMO.md): one trace, six failed checks with evidence, and the corrected result.
* [Walkthroughs](walkthroughs/README.md): seven worked examples, each built on a recorded trace, including [reading the trace when a check fails](walkthroughs/09-read-the-trace.md). Bring an agent trace, contribute a test.
* [Learning roadmap](LEARNING-ROADMAP.md): a path from first agent test to red teaming and privacy, mapped to checklist IDs and tutorials. [Build your own agent test](BUILD-YOUR-OWN-AGENT-TEST.md): the four steps from scratch and a recipe per checklist family. [Interview questions and flashcards](INTERVIEW-QUESTIONS.md).
* [Test planning and manual review with the 110 designs](guides/TEST-PLANNING-WITH-THE-CHECKLIST.md): turn the checklist into a test plan, review by hand, fill it with verdicts, implement designs in your own harness; [course exercise and notebook](../examples/course/README.md).
* [Tutorials](tutorials/README.md): see the [Tutorials](#tutorials) section above. Each tutorial has a Colab notebook under [notebooks/tutorials](../notebooks/tutorials/).
* [Recipes](recipes/README.md): [judge inputs generated by any tool](recipes/judge-generated-inputs.md) and [scheduled runs](recipes/scheduled-runs.md). Both continue from [Start here](START_HERE.md#the-path).
* [Challenge: can your AI agent pass these tests?](CHALLENGE.md): run the checks on your own traces in four steps; no prize, no ranking.
* [Wall of caught failures](WALL-OF-CAUGHT-FAILURES.md): real failures agentest flagged in recorded runs of the bundled reference agents, each with a one-command repro from PyPI.
* [Use cases](../examples/use_cases/README.md): one recorded failure per case, with the check, the command and the printed result. Full tables stay on the wall.
* [Agentic evals challenge](../challenge/README.md): 20 example traces to diagnose, with a [leaderboard](../challenge/LEADERBOARD.md) for contributor week (23 to 30 November 2026).
* ["Tested with agentest" badge](TESTED-WITH-AGENTEST.md): a badge and a snippet you can copy into your README.
* [Adopters](ADOPTERS.md): how to share a run in [Show and tell](https://github.com/srpadmanabhuni/agentest/discussions/categories/show-and-tell) ([Discussion #265](https://github.com/srpadmanabhuni/agentest/discussions/265)).
* [Roadmap](ROADMAP.md), pinned as [issue #272](https://github.com/srpadmanabhuni/agentest/issues/272). Suggestions: [Discussion #80](https://github.com/srpadmanabhuni/agentest/discussions/80).
* [Agent failure report](AGENT-FAILURE-REPORT.md): four reference agents that failed specific checks on recorded runs, with the one command to rerun each, and what agentest does not catch.
* [Notebook quickstart](../examples/colab_quickstart.ipynb): the bundled good and buggy agents, free CPU, no login and no model. `python examples/colab_quickstart.py` from a clone.
* [Release highlights](RELEASE-HIGHLIGHTS.md), [Selected references](READING-LIST.md), [About and citation](ABOUT.md).
* [Contributing tools](contributing/EVAL.md): `make eval` shows what your change does to the verdicts on the public example agents; [CI verdict diff](contributing/CI-VERDICT-DIFF.md); [label 10 traces](contributing/LABELLING.md).
* [Agent-independence audit](standards/AGENT-INDEPENDENCE-AUDIT.md): evidence that no check depends on a particular agent.

## Translations

- [Hindi: Five checklist titles](i18n/hi/checklist-titles-5.md)

## Testers (track: User Guide, then these)

* [Reading results](testers/READING-RESULTS.md)
* [Per-test guide](testers/PER-TEST-GUIDE.md)
* [Test planning by priority and standard](testers/TEST-PLANNING.md)
* [Generating inputs](testers/GENERATING-INPUTS.md)
* [False positives and heuristics](testers/FALSE-POSITIVES.md)
* [Writing defect reports](testers/DEFECT-REPORTS.md)
* [Glossary](testers/GLOSSARY.md)
* [Per-ID test pages](tests/README.md)

## Developers (track: Author Guide, then these)

* [Author Guide](AUTHOR-GUIDE.md)
* [Concepts](developers/CONCEPTS.md)
* [Standards primer](developers/STANDARDS-PRIMER.md)
* [Instrumenting your agent](developers/INSTRUMENTING.md)
* How to test agents with OpenTelemetry and agentest: [LangGraph](integrations/langgraph.md) (dialect `langgraph_msgs`, example at `examples/langgraph_import/`), [LlamaIndex](integrations/llamaindex.md) (dialect `events`, example at `examples/llamaindex_import/`), [CrewAI](integrations/crewai.md) (no built-in dialect; recorded runs in `agents/`), [OpenAI Agents SDK](integrations/openai-agents-sdk.md), [AutoGen](integrations/autogen.md), [smolagents](integrations/smolagents.md), [Vercel AI SDK](integrations/ai-sdk.md) (UIMessage tool parts, example at `examples/ai_sdk_import/`), [Google ADK](integrations/google-adk.md), [n8n](integrations/n8n.md), [MCP](integrations/mcp.md).
* [Writing the AgentCard](developers/AGENT-CARD.md)
* [Onboarding a new agent](developers/ONBOARDING.md)
* [Adding rules and plugins](developers/ADDING-RULES.md)
* [CLI and API reference](developers/REFERENCE.md)
* [CI integration](developers/CI.md)
* [GitHub Action and pre-commit hook](developers/GITHUB-ACTION.md)
* [Troubleshooting](developers/TROUBLESHOOTING.md)

## Standards engine (v3)

* [Design](standards/DESIGN.md)
* [Standards map](standards/STANDARDS-MAP.md)
* [Governance extension](standards/EXTENSION.md)
* [Trace format 1.0.0: every attribute the checks read](TRACE-FORMAT.md)
* [Connectors: emitting the trace format](CONNECTORS.md)
* [Extension packs (opt-in, outside the 165 tests)](packs/README.md): multi-agent, privacy, red-teaming, bias and fairness, explainability, data lineage
* [Regression against v2](standards/REGRESSION.md) (v3.0.0 record; v3.1.0 keeps that floor)
* [Engine developer guide](standards/DEVELOPER-GUIDE.md)

## Background

* [Agent failure taxonomy v0.1](taxonomy/TAXONOMY.md) and the [check to OWASP Agentic Top 10 mapping](taxonomy/ASI-MAPPING.md)
* [Failure registry](../registry/README.md): reproducible agent failures with stable IDs ([index](registry/INDEX.md))
* [Framework mapping](FRAMEWORK-MAPPING.md), [References](REFERENCES.md), [Test sources](TEST-SOURCES.md)
* [Explainability research](EXPLAINABILITY-RESEARCH.md), [Bias research](BIAS-RESEARCH.md)

## Historical notes (v0.x to v2; the code they describe was removed, see the `v1.0.0` and `v2.0.0` tags)

* [Sample agents](history/SAMPLE-AGENTS.md), [Scenarios 8-10](history/SCENARIOS-8-10.md), [Expected-fail scenarios](history/SCENARIOS-EXPECTED-FAIL.md), [Orchestration](history/ORCHESTRATION.md)
* [Explainability oracle](history/EXPLAINABILITY-ORACLE.md), [Proposed bias expansion](history/PROPOSED-bias.md)
* Milestone backlogs: [M0](history/M0-BACKLOG.md), [M1](history/M1-BACKLOG.md), [M2](history/M2-BACKLOG.md), [M3](history/M3-BACKLOG.md), [M4](history/M4-BACKLOG.md), [M5](history/M5-BACKLOG.md)

The v1 `agentest check` / `run` / `samples` / `matrix` commands, the v2 `agentest real` / `agentest model` engine,
`profiles/`, `reference_agents/` sources and `fixtures/real/` were removed in v3.1.0. Reference-agent source code
lives in the reference-agents repository; only each agent's standard files are bundled under `agents/`.
