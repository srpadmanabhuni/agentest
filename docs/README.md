# Documentation index

## Start here
* [User Guide](USER-GUIDE.md): install, quickstart on your own traces, modes, CLI, config, outputs, CI, FAQ.
* [Author Guide](AUTHOR-GUIDE.md): new universal rules, scenarios, framework adapters, extension fields, reference agents, guards, contribution checklist.
* [Tester quickstart](testers/QUICKSTART.md): run the checks in five minutes.
* [Coverage on the reference agents](COVERAGE.md) (generated, checked in CI).
* [No lock-in](NO-LOCK-IN.md): what is guaranteed and what the residual risks are.
* [Agent-independence audit](standards/AGENT-INDEPENDENCE-AUDIT.md): evidence that no check depends on a particular agent.

## Testers (track: User Guide, then these)
* [Reading results](testers/READING-RESULTS.md)
* [Per-test guide: all 130 IDs](testers/PER-TEST-GUIDE.md)
* [Test planning by priority and standard](testers/TEST-PLANNING.md)
* [Generating inputs](testers/GENERATING-INPUTS.md)
* [False positives and heuristics](testers/FALSE-POSITIVES.md)
* [Writing defect reports](testers/DEFECT-REPORTS.md)
* [Glossary](testers/GLOSSARY.md)
* [Per-ID test pages](tests/README.md)

## Developers (track: Author Guide, then these)
* [Concepts](developers/CONCEPTS.md)
* [Standards primer](developers/STANDARDS-PRIMER.md)
* [Instrumenting your agent](developers/INSTRUMENTING.md)
* [Writing the AgentCard](developers/AGENT-CARD.md)
* [Onboarding a new agent](developers/ONBOARDING.md)
* [Adding rules and plugins](developers/ADDING-RULES.md)
* [CLI and API reference](developers/REFERENCE.md)
* [CI integration](developers/CI.md)
* [Troubleshooting](developers/TROUBLESHOOTING.md)

## Standards engine (v3)
* [Design](standards/DESIGN.md)
* [Standards map](standards/STANDARDS-MAP.md)
* [Governance extension](standards/EXTENSION.md)
* [Regression against v2](standards/REGRESSION.md) (v3.0.0 record; v3.1.0 keeps that floor)
* [Engine developer guide](standards/DEVELOPER-GUIDE.md)

## Background
* [Framework mapping](FRAMEWORK-MAPPING.md), [References](REFERENCES.md), [Test sources](TEST-SOURCES.md)
* [Explainability research](EXPLAINABILITY-RESEARCH.md), [Bias research](BIAS-RESEARCH.md)

## Historical notes (v0.x to v2; the code they describe was removed, see the `v1.0.0` and `v2.0.0` tags)
* [Sample agents](SAMPLE-AGENTS.md), [Scenarios 8-10](SCENARIOS-8-10.md), [Expected-fail scenarios](SCENARIOS-EXPECTED-FAIL.md), [Orchestration](ORCHESTRATION.md)
* [Explainability oracle](EXPLAINABILITY-ORACLE.md), [Proposed bias expansion](PROPOSED-bias.md)
* Milestone backlogs: [M0](M0-BACKLOG.md), [M1](M1-BACKLOG.md), [M2](M2-BACKLOG.md), [M3](M3-BACKLOG.md), [M4](M4-BACKLOG.md), [M5](M5-BACKLOG.md)

The v1 `agentest check` / `run` / `samples` / `matrix` commands, the v2 `agentest real` / `agentest model` engine,
`profiles/`, `reference_agents/` sources and `fixtures/real/` were removed in v3.1.0. Reference-agent source code
lives in the reference-agents repository; only each agent's standard files are bundled under `agents/`.
