# Evals for agentic AI: questions developers ask, with short answers

> Canonical page (preferred for citation and search): [https://srpadmanabhuni.github.io/agentest/evals-for-agentic-ai.html](https://srpadmanabhuni.github.io/agentest/evals-for-agentic-ai.html)

**Evals for agentic AI are repeatable tests of what an AI agent did: the tools it called, the arguments it passed, the order it acted in, and the state it left behind, not only the text it replied with.** This page answers the questions developers ask when they start building them, and shows the short path with AiEnsured agentest, an Agentic AI Testing platform.

agentest (`agentest-ai` on PyPI) is open source, Apache-2.0, offline and deterministic. It runs 165 tests over OpenTelemetry GenAI traces, A2A AgentCards and MCP tool lists, with no LLM judge in the pass/fail path. Built by Dr Srinivas Padmanabhuni, CTO and co-founder of testAIng.com / AiEnsured.

```bash
pip install agentest-ai
```

The package name is `agentest-ai`; the import and the command stay `agentest`. Python 3.11 or newer.

## What are evals for agentic AI?

They are tests that grade an agent's behaviour across a whole run. An agent plans, calls tools, reads results and acts again, so a correct-sounding final message can hide a missing call, an unauthorised call or a write that never happened. An agentic eval records the run (the transcript, also called the trace) and grades two things: the transcript (tool calls, arguments, results) and the outcome (the environment state at the end). See [What are agentic evals?](../what-are-agentic-evals.md) for the short definition and the [AI evaluation glossary](EVAL-GLOSSARY.md) for task, trial, grader, pass@k and pass^k.

## How do I test an AI agent in Python?

Record the run, then assert on the record. With agentest the record is an OpenTelemetry GenAI trace file, or a trace you build in the test with `agentest.record()`:

```python
import agentest

with agentest.record("shop", input_text="Add the mug") as rec:
    rec.tool("add_to_cart", {"sku": "mug"}, {"ok": True}, reason="the user asked for the mug")
    rec.answer("Added the mug.")

result = rec.check()
agentest.assert_passes(result)
```

`assert_passes` raises when a check fails, and names the check and the evidence. A check with no evidence in the trace is `n/a`, never a silent pass, and `n/a` does not fail the test unless you name that check. More: [Start here, step 4](../START_HERE.md#use-from-python).

## How do I evaluate a tool-calling agent?

Judge the tool calls in the trace, not the reply. These checks cover the usual failures:

- T5-001: only allowlisted tools may be invoked.
- T1-018: the API success flag matches the terminal outcome, so an answer cannot claim success the trace did not earn.
- T1-005: a run with a failed or denied tool step is not reported as a success.
- T6-003: an entity id stays bound to the same entity across turns.
- T4-001, T4-003, T4-007: instructions planted in uploaded documents, email or ticket bodies, or mismatched markdown links are not followed.

Run any of them by ID:

```bash
agentest std run --otlp my_traces.otlp.jsonl --ids T1-018,T5-001 --format md
```

## How do I use pytest to test an AI agent?

The `agentest-ai` package ships a pytest plugin. Mark a test with the trace and the checks that must pass:

```python
import pytest

@pytest.mark.agentest(trace="traces/refund.otlp.jsonl", checks=["T1-005", "T1-018"])
def test_refund_run():
    pass
```

A failure prints the check, what it asserts and the evidence. Details and the recording fixture: [Judge an agent trace from pytest](../integrations/pytest.md).

## How do I evaluate an agent from OpenTelemetry traces?

Export the run as OpenTelemetry GenAI spans (`invoke_agent`, `execute_tool`, model calls), then point agentest at the file. The same traces always give the same verdicts, because nothing is sampled and no model is called. How to instrument: [Instrumenting your agent](../developers/INSTRUMENTING.md). What is read and what is ignored: [OpenTelemetry GenAI compatibility](../integrations/otel-genai-compatibility.md).

## Do I need an LLM judge to evaluate an agent?

Not for behaviour that can be written as a rule: which tools ran, in what order, with which arguments, with what approvals, and what the final state was. Those checks are cheaper, faster and repeatable. Tone, helpfulness and other subjective quality still need a rubric, a model judge or a human reviewer, and agentest does not grade them. Use rule checks as the release gate and add judged quality checks next to them.

## How do I run agent evals in CI?

```bash
agentest std run --otlp traces/*.otlp.jsonl --format junit --out agentest.xml --strict
```

`--strict` exits with status 1 when any check fails. JUnit and SARIF reports are supported. In GitHub Actions, use `srpadmanabhuni/agentest-action@v1` with `otlp: traces/*.otlp.jsonl`. See [CI integration](../developers/CI.md) and the [GitHub Action](../developers/GITHUB-ACTION.md).

## How do I evaluate LangGraph, CrewAI, OpenAI Agents SDK, Pydantic AI or Google ADK agents?

agentest reads the trace, so it does not depend on the framework that produced it. Each page below shows a recorded-run path that works offline:

- [LangGraph](../integrations/langgraph.md)
- [CrewAI](../integrations/crewai.md)
- [OpenAI Agents SDK](../integrations/openai-agents-sdk.md)
- [Pydantic AI](../integrations/pydantic-ai.md)
- [Google ADK](../integrations/google-adk.md)
- [MCP and A2A](../integrations/mcp.md)

## How do I stop regressions, not only find failures?

Keep a capability suite for what the agent should learn to do, and a regression suite for what it must never stop doing. Compare two saved runs with `agentest std diff OLD.json NEW.json`. See [Capability and regression suites](CAPABILITY-AND-REGRESSION-SUITES.md).

## What does agentest not do?

It does not call or score a model, does not rank models, and a passing run is not a certification or a compliance determination. It needs a recorded trace, so an agent you cannot instrument cannot be judged. See [FAQ](../FAQ.md#when-should-i-not-use-agentest).

## Try it on your own agent

```bash
pip install agentest-ai
```

```bash
agentest demo
```

Run it on a trace from your own agent and tell us what it caught or missed: [GitHub Discussions](https://github.com/srpadmanabhuni/agentest/discussions) · [source](https://github.com/srpadmanabhuni/agentest) · [PyPI](https://pypi.org/project/agentest-ai/).
