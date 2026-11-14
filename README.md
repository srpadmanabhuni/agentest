# agentest

> **Is your AI agent lying about what it did? Find out in 60 seconds.**

**Test AI agents with 130 executable checks. Open source, deterministic, and framework-independent.**

[![CI](https://github.com/srpadmanabhuni/agentest/actions/workflows/ci.yml/badge.svg)](https://github.com/srpadmanabhuni/agentest/actions/workflows/ci.yml) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE) [![Hugging Face checklist](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Checklist%20110-yellow.svg)](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/examples/colab_quickstart.ipynb)

agentest reads the traces your agent already recorded and tells you, check by check, what it did wrong: claimed success it did not earn, acted before verifying, followed an instruction hidden in a document, called a tool it should not, or leaked personal data. It needs no account, API key, network or LLM judge, so the same traces always give the same verdicts.

**Who it is for:** developers shipping tool-using agents, QA and test engineers who need something to run in CI, and reviewers who want evidence rather than opinions.

## 60-second first win

Python 3.11+, nothing else. This runs agentest on a bundled sample agent that has seeded bugs:

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git && cd agentest
python3 -m venv .venv && . .venv/bin/activate && pip install -q -e .
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy \
  --ids T1-018,T2-001,T4-003,T7-014 --format md
```

It prints a caught-bug report: one line of evidence per failed check.

![Four failed checks on the buggy sample agent. T1-018: claims success. T2-001: place_refill before verify_identity. T4-003: injected recipient audit@evil.example. T7-014: unmasked email.](docs/img/caught-bug.png)

*A rendering of the real output, with a plain-English label added per check. The evidence text is verbatim (T2-001 shortened); the plain `--format md` output is a table of the same rows.*

For contrast, the clean sibling agent passes everything it can be judged on: `agentest std run --agents examples/agnostic_demo/agents --agent refill_bot` prints `refill_bot: 55 pass, 0 fail`. Prefer a notebook? [Open the Colab](https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/examples/colab_quickstart.ipynb) (free CPU, no login, no model), or run `python examples/colab_quickstart.py` from the clone for the full before-and-after walkthrough.

## Now point it at your agent

```bash
# 1. Judge your agent's OpenTelemetry GenAI traces
agentest std run --otlp my_traces.otlp.jsonl

# 2. Optionally add its A2A AgentCard and MCP tools list for more checks
agentest std run --otlp my_traces.otlp.jsonl --card agent-card.json --tools tools.json

# 3. Gate CI (also json, sarif, html, md, csv)
agentest std run --otlp my_traces.otlp.jsonl --format junit --out agentest.xml --strict
```

No traces yet? [Emit one with the standard library](examples/otel_plain/emit_trace.py), [import a native log](docs/walkthroughs/05-bring-your-own-log.md), or [use LangGraph](docs/integrations/langgraph.md) (run `python examples/langgraph_import/test_langgraph.py` for an offline example). A check with no evidence in your trace says `n/a`, never a silent `pass`.

> `pip install agentest-ai` does not work yet: the PyPI release is pending. Until then install from GitHub: `pip install git+https://github.com/srpadmanabhuni/agentest`. More options: [install and quickstart](docs/INSTALL-AND-QUICKSTART.md).

## What it checks

130 checks: the 110 tests of the open [Agentic AI Test Checklist 110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) on Hugging Face, plus 20 repo extensions (`X-001`...`X-020`).

| Class | Checks | Catches, for example |
|---|---:|---|
| T1 Task success and terminal state | 18 | Claims success it did not earn (`T1-018`); writes outside scope (`T1-004`) |
| T2 Dependency ordering | 14 | Irreversible action before its prerequisite (`T2-001`) |
| T3 Control handover and authorisation | 14 | Gated action with no recorded approval (`T3-006`) |
| T4 Prompt injection from untrusted documents | 18 | A hidden instruction changes who gets the email (`T4-003`) |
| T5 Tool-call allowlists | 18 | Undeclared tool or disallowed host (`T5-001`, `T5-005`) |
| T6 State drift across turns | 14 | An amount or ID silently changes between turns (`T6-002`, `T6-003`) |
| T7 Metamorphic and consistency | 14 | Personal data left unmasked (`T7-014`) |
| X Repo extensions | 20 | Extra checks, listed in the [per-ID pages](docs/tests/README.md) |

Why it is different: it runs offline, uses no LLM judge, reads open standards (OpenTelemetry GenAI, A2A AgentCard, MCP tool annotations) and never asks your agent to import it ([No lock-in](docs/NO-LOCK-IN.md), [agent-independence audit](docs/standards/AGENT-INDEPENDENCE-AUDIT.md)). Limits, known false positives and coverage are in [How it works](docs/HOW-IT-WORKS.md). Not certification.

## Learn more

| I want to | Go to |
|---|---|
| Understand it in ten minutes | [Why agentest: developers](docs/guides/WHY-AGENTEST-FOR-DEVELOPERS.md), [testers](docs/guides/WHY-AGENTEST-FOR-TESTERS.md) |
| See a full bug-detection story | [Demo: trace, failed check, evidence, corrected result](docs/demos/BUG-DETECTION-DEMO.md) |
| Walk through real failures | [Walkthroughs](docs/walkthroughs/README.md) |
| Install, CLI, config, CI | [Getting started](docs/GETTING-STARTED.md), [User Guide](docs/USER-GUIDE.md), [CI](docs/developers/CI.md) |
| Read a report | [Reading the report](docs/READING-THE-REPORT.md) |
| See every document | [Documentation index](docs/README.md), [FAQ](docs/FAQ.md) |
| Know how it works and where it stops | [How it works and coverage](docs/HOW-IT-WORKS.md), [Roadmap](docs/ROADMAP.md) |
| Browse the checklist | [Hugging Face dataset](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110), [how GitHub and HF fit together](docs/CATALOGUE-AND-HF.md) |

## Contribute

You do not need to be an agent expert. Pick a [`good first issue`](https://github.com/srpadmanabhuni/agentest/labels/good%20first%20issue), follow [the ten-minute first pull request](CONTRIBUTING.md#your-first-pull-request-in-about-ten-minutes), or bring a redacted agent trace to [Discussions](https://github.com/srpadmanabhuni/agentest/discussions). Theme: *Bring an agent trace, contribute a test.* Wrong verdict? Use the [issue forms](https://github.com/srpadmanabhuni/agentest/issues/new/choose). Please follow the [Code of Conduct](CODE_OF_CONDUCT.md). If agentest catches a bug for you, a star helps others find it.

## Author, citation, licence

By Dr Srinivas Padmanabhuni, CTO and Co-founder, AiEnsured (testAIng.com). Contact: srinivas AT testAIng.com. Cite with DOI [10.5281/zenodo.23597877](https://doi.org/10.5281/zenodo.23597877) (all versions) or [`CITATION.cff`](CITATION.cff); details in [About](docs/ABOUT.md). Runner: Apache-2.0 ([LICENSE](LICENSE)); checklist data: CC BY 4.0. Catalogue: pinned catalogue **v1.3.1** ([`catalog/VERSION`](catalog/VERSION)). Selected [references](docs/READING-LIST.md); [release highlights](docs/RELEASE-HIGHLIGHTS.md).
