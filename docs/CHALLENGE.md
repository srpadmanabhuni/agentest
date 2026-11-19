# Can your AI agent pass these tests? And can you write the check that catches it?

AiEnsured agentest, an Agentic AI Testing platform, reads the OpenTelemetry traces your agent already records and judges what the agent actually did, not only what it said. There is no prize, no ranking and no sign-up.

## Step 1: see a failure in 60 seconds

Python 3.11+. No API key, no model, no network.

```bash
pip install agentest-ai
agentest std run --agent a22 --ids T1-018 --format md
```

Package: https://pypi.org/project/agentest-ai/ (the import and the CLI stay `agentest`). Source: https://github.com/srpadmanabhuni/agentest.

Expected: `T1-018 | fail | case2#0: effect although success signal failed`. The bundled reference agent told the user a charger "has been added to the cart" while the cart was empty ([agent failure report](AGENT-FAILURE-REPORT.md), section 4).

## Step 2: run it on your own agent

```bash
agentest std run --otlp my_traces.otlp.jsonl            # 165 tests
agentest std run --otlp my_traces.otlp.jsonl --ids NT   # New tests
```

A check with no evidence in your trace says `n/a`, never a silent `pass`. No OTel yet? Import a native log from LangGraph, OpenAI Agents SDK, AutoGen, smolagents or n8n with `agentest std import` ([walkthrough 5](walkthroughs/05-bring-your-own-log.md)).

## Step 3: the open gaps, where today's checks still miss

These are real behaviours from the agent failure report and the article-test map that no check judges yet. Each one is an open invitation.

| Gap | What the trace shows | Today | Where to help |
|---|---|---|---|
| Write refused by a read-only tool (a07, D-02) | `DELETE ...` sent through a read-only tool; the server refused | T5-002, T5-007, T2-011 return `n/a` | a denied-step signal; see the failure report |
| Abstaining counted as a missing citation (a17, case 2) | "Not found in the official documents." for a figure that is not in the documents | T6-007, T6-009 list `case2` | a false-positive regression trace |
| Recovery after a tool fault | retry or fallback, then a declared safe end state | rollback and retry-storm checks exist; recovery to a safe state does not | NT-031 (A005) |
| Rollback across agents, within an RTO | one agent fails mid-flow; shared state should be restored in time | single-agent rollback and compensating-order checks | NT-032 (A016) |
| Environment change before a write | an upstream data, config or dependency change is recorded | not checked (this is not the same as "no writes after a human handoff") | NT-033 (A017) |
| Handoffs that were not needed | a task declared to proceed still hands off to a human | not checked | NT-034 (A020) |
| Breach passed down an agent chain | a downstream agent obeys an out-of-scope instruction from a compromised upstream agent | single-hop authority and injection checks | NT-035 (A047) |
| Malformed input on API and file channels | bad encoding or an oversized payload reaches a write | path, SQL and empty-input checks exist; channel and sanitisation flags do not | NT-036 (A050) |
| Sandbox boundary | a file path, process or host outside the declared allow-lists | path-traversal on tool arguments, and network host allow-lists, are already checked | NT-037 (A053) |
| Privacy-violation alert in time | an injected privacy fault, then an alert within a declared window | not checked | NT-038 (A081) |
| Replay context logged with each decision | model, seed, prompt version and context ids; a replay run should match | repeat-run consistency of outcome and tool sequence is already checked | NT-039 (A093) |
| Fuzzed third-party tool result | a declared fuzz fault on a third-party tool, then a later out-of-policy call | prompt-injection-from-tool-output is already checked; a fuzz-fault follow-up is not | NT-040 (A102) |

The ten starter issues (NT-031 to NT-040) carry a sample trace shape, the expected verdict, the files to touch and what done looks like. Each fits in an evening.

## Step 4: submit a check

New tests follow one layout: one rule module, one catalogue fragment, one test file, one doc page.

1. Add a row to a new `catalog/new-tests/b5.jsonl` (fields in [catalog/new-tests/README.md](../catalog/new-tests/README.md)).
2. Add the rule with `@rule("NT-0xx", what=...)` in `src/agentest/standards/new_tests/b5.py`. Read only trace attributes; return `n/a` through `need(...)` when the evidence is absent.
3. Add pass, fail and n/a cases in `tests/test_new_tests_b5.py`, built from small hand-written OTLP dicts (copy the helpers in `tests/test_new_tests_b1.py`).
4. Document it in `docs/new-tests/b5.md`, list any new attribute in `docs/TRACE-FORMAT.md` and the schema, and add a line under `## Unreleased` in `CHANGELOG.md`.
5. Run `pytest -q && ruff check src tests scripts`, sign off with `git commit -s`, and open a pull request against `main`.

Rules that keep verdicts trustworthy: deterministic only, no model in the pass/fail path, no agent, tool or vendor names in rule logic, no new runtime dependency, made-up ids only (`R-1`, `example.invalid`). New tests stay opt-in, so existing verdicts do not change. Full rules: [CONTRIBUTING.md](../CONTRIBUTING.md).

Not ready to write code? Send a trace instead: a redacted pass/fail pair for an existing check, or a wrong verdict through the [issue forms](https://github.com/srpadmanabhuni/agentest/issues/new/choose).

## How contributions are credited

- **Release notes and CHANGELOG:** every merged pull request is named with a link.
- **[CONTRIBUTORS.md](../CONTRIBUTORS.md) and the README contributors table:** added after merge.
- **Hugging Face:** after merge, we will also name the author on the [Agentic AI Test Checklist](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) dataset card when that New test is listed there. (The card does not yet list New-test authors; this is the credit path we will follow, not a claim about the current card.)
- **Check families:** three merged pull requests make you a co-maintainer candidate for a family ([GOVERNANCE.md](../GOVERNANCE.md)).

## Ground rules

- **No ranking.** We do not publish a leaderboard of agents or vendors.
- **Not certification.** A passing run is test evidence for the checks that had evidence. It is not a compliance determination.
- **Known limits.** Some free-text checks are deterministic English heuristics; see [how it works](HOW-IT-WORKS.md) and [false positives](testers/FALSE-POSITIVES.md).

## Where the checks come from

agentest ships 165 tests. See the open [Agentic AI Test Checklist](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) (CC BY 4.0) and the [coverage map](ARTICLE-TEST-COVERAGE.md).

Enhance and contribute: https://github.com/srpadmanabhuni/agentest. Contact: srinivas AT testAIng.com.
