# AiEnsured agentest, an Agentic AI Testing platform

> **Catches AI agents that say "done" when they did not do it.** agentest runs 130 executable checks on the traces your agent already recorded: open source, offline, deterministic, no LLM judge. Built for agent developers and QA engineers.

[![Demo: an agent says "added to the cart", its trace shows no add_to_cart call and an empty cart, and agentest reports a fail on check T1-018](https://raw.githubusercontent.com/srpadmanabhuni/agentest/main/docs/assets/demo-empty-cart.gif)](https://github.com/srpadmanabhuni/agentest/blob/main/docs/assets/agentest-demo-empty-cart.mp4)

*A real recorded run of a shopping agent in a mock shop (nothing was bought). Click the image to [watch the 56-second video with voiceover](https://github.com/srpadmanabhuni/agentest/blob/main/docs/assets/agentest-demo-empty-cart.mp4).*

[![CI](https://github.com/srpadmanabhuni/agentest/actions/workflows/ci.yml/badge.svg)](https://github.com/srpadmanabhuni/agentest/actions/workflows/ci.yml) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/srpadmanabhuni/agentest/blob/main/LICENSE) [![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://github.com/srpadmanabhuni/agentest/blob/main/pyproject.toml) [![Docs](https://img.shields.io/badge/docs-index-blue.svg)](https://github.com/srpadmanabhuni/agentest/blob/main/docs/README.md) [![Hugging Face checklist](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Checklist%20110-yellow.svg)](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/examples/colab_quickstart.ipynb)

If this saves you time, consider giving it a ⭐ to help others find it.

## Try it

**No install, in your browser:** the [Assurance Report Card](https://huggingface.co/spaces/srinivaspadmanabhuni/agentest-assurance-report-card) (paste or upload a trace and see which checks fail; three samples included) or [Open in Colab](https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/examples/colab_quickstart.ipynb) (free CPU, no login, no model).

**From source, three lines** (Python 3.11+, no API key, no model). This reproduces the run in the clip above:

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git && cd agentest
python3 -m venv .venv && . .venv/bin/activate && pip install -q -e .
agentest std run --agent a22 --ids T1-018 --format md
```

Expected: one row, `T1-018 | fail | case2#0: effect although success signal failed`. The PyPI package `agentest-ai` is pending, so install from GitHub as above ([all install options](https://github.com/srpadmanabhuni/agentest/blob/main/docs/INSTALL-AND-QUICKSTART.md)).

If that run was useful, a ⭐ helps other people find agentest.

<p>
  <sub>Built by</sub><br>
  <a href="https://www.aiensured.com/"><img src="https://raw.githubusercontent.com/srpadmanabhuni/agentest/main/docs/img/brand/aiensured.png" alt="AiEnsured" height="48"></a>
  &nbsp;&nbsp;
  <a href="https://www.testaing.com/"><img src="https://raw.githubusercontent.com/srpadmanabhuni/agentest/main/docs/img/brand/testaing.png" alt="testAIng" height="48"></a>
</p>

> **Launched 15 Nov 2026.** Try it from source in under 3 minutes. Then take the [challenge](https://github.com/srpadmanabhuni/agentest/blob/main/docs/CHALLENGE.md), or open a [good first issue](https://github.com/srpadmanabhuni/agentest/labels/good%20first%20issue).

> **New here? [Start here](https://github.com/srpadmanabhuni/agentest/blob/main/docs/START_HERE.md)**: what an agent test is, a three-step first run (about 10 seconds), how to read the result, and how to test your own agent.

agentest reads the traces your agent already recorded and tells you, check by check, what it did wrong: claimed success it did not earn, acted before verifying, followed an instruction hidden in a document, called a tool it should not, or leaked personal data. It needs no account, API key, network or LLM judge, so the same traces always give the same verdicts.

**Who it is for**

- **Agent developers:** catch broken tool calls, unearned "Done!" replies and prompt injection before your users do. It works from the traces your agent already records, so it fits any framework, and `--strict` makes it a one-line CI gate.
- **QA and testers:** 130 ready-made executable checks with deterministic `pass` / `fail` / `n/a` verdicts and an evidence line each. No LLM judge, so no flaky scores. It reads OpenTelemetry GenAI traces, A2A AgentCards and MCP tool lists.

**Why agentest:** one open suite of 130 executable checks spanning evals, security, privacy and responsible behaviour; it judges what your agent *did* (tool calls and results), not only what it *said*; and it is deterministic and offline, with no LLM judge, API key or network. It reads open OpenTelemetry GenAI, A2A and MCP data from any framework and gates CI. [Every point, with its source](https://github.com/srpadmanabhuni/agentest/blob/main/docs/START_HERE.md#what-makes-agentest-different). Use it for a [pre-release gate, regression checks after a prompt change, security review, or evaluating another team's agent](https://github.com/srpadmanabhuni/agentest/blob/main/docs/START_HERE.md#use-it-for).

**Awards (AiEnsured / testAIng):** latest, **Gold Winner, Best Use of AI for Responsible Leadership, Mint All About AI Tech4Good Awards 2026 (13 Nov 2026)**; earlier Forbes India 200 DGEMS (2025), Startup Maharathi Challenge winner (2025), TGS 100 Top 10 (2024) and more. [Full list with sources](https://github.com/srpadmanabhuni/agentest/blob/main/docs/START_HERE.md#awards-and-recognition-aiensured--testaing).

**Your move:** [try it](#try-it), take the [challenge: can your agent pass these tests?](https://github.com/srpadmanabhuni/agentest/blob/main/docs/CHALLENGE.md); or open a [good first issue](https://github.com/srpadmanabhuni/agentest/labels/good%20first%20issue).

## 60-second first win

A longer run: Python 3.11+, nothing else. This runs agentest on a bundled sample agent that has seeded bugs and checks four things at once:

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git && cd agentest
python3 -m venv .venv && . .venv/bin/activate && pip install -q -e .
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy \
  --ids T1-018,T2-001,T4-003,T7-014 --format md
```

It prints a caught-bug report: one line of evidence per failed check.

![Four failed checks on the buggy sample agent. T1-018: claims success. T2-001: place_refill before verify_identity. T4-003: injected recipient audit@evil.example. T7-014: unmasked email.](https://raw.githubusercontent.com/srpadmanabhuni/agentest/main/docs/img/caught-bug.png)

*A rendering of the real output, with a plain-English label added per check. The evidence text is verbatim (T2-001 shortened); the plain `--format md` output is a table of the same rows.*

For contrast, the clean sibling agent passes everything it can be judged on: `agentest std run --agents examples/agnostic_demo/agents --agent refill_bot` prints `refill_bot: 55 pass, 0 fail`. The same before-and-after walkthrough is in the [Colab](https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/examples/colab_quickstart.ipynb) above, or run `python examples/colab_quickstart.py` from the clone.

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

> `pip install agentest-ai` does not work yet: the PyPI release is pending. Until then install from GitHub: `pip install git+https://github.com/srpadmanabhuni/agentest`. More options: [install and quickstart](https://github.com/srpadmanabhuni/agentest/blob/main/docs/INSTALL-AND-QUICKSTART.md).

## What it checks

130 checks: the 110 tests of the open [Agentic AI Test Checklist 110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) on Hugging Face, plus 20 repo extensions (`X-001`...`X-020`).

Load the 47 highest-priority test designs in three lines (config `all` has all 110; details in [Catalogue and Hugging Face](https://github.com/srpadmanabhuni/agentest/blob/main/docs/CATALOGUE-AND-HF.md)):

```python
from datasets import load_dataset
ds = load_dataset("srinivaspadmanabhuni/agentic-ai-test-checklist-110", "p0_smoke", split="train")
print(ds[0]["id"], ds[0]["title"])  # T1-001  Terminal postconditions hold after a single agent task
```


| Class | Checks | Catches, for example |
|---|---:|---|
| T1 Task success and terminal state | 18 | Claims success it did not earn (`T1-018`); writes outside scope (`T1-004`) |
| T2 Dependency ordering | 14 | Irreversible action before its prerequisite (`T2-001`) |
| T3 Control handover and authorisation | 14 | Gated action with no recorded approval (`T3-006`) |
| T4 Prompt injection from untrusted documents | 18 | A hidden instruction changes who gets the email (`T4-003`) |
| T5 Tool-call allowlists | 18 | Undeclared tool or disallowed host (`T5-001`, `T5-005`) |
| T6 State drift across turns | 14 | An amount or ID silently changes between turns (`T6-002`, `T6-003`) |
| T7 Metamorphic and consistency | 14 | Personal data left unmasked (`T7-014`) |
| X Repo extensions | 20 | Extra checks, listed in the [per-ID pages](https://github.com/srpadmanabhuni/agentest/blob/main/docs/tests/README.md) |

Why it is different: it runs offline, uses no LLM judge, reads open standards (OpenTelemetry GenAI, A2A AgentCard, MCP tool annotations) and never asks your agent to import it ([No lock-in](https://github.com/srpadmanabhuni/agentest/blob/main/docs/NO-LOCK-IN.md), [agent-independence audit](https://github.com/srpadmanabhuni/agentest/blob/main/docs/standards/AGENT-INDEPENDENCE-AUDIT.md)). Limits, known false positives and coverage are in [How it works](https://github.com/srpadmanabhuni/agentest/blob/main/docs/HOW-IT-WORKS.md). Not certification.

## Roadmap

Open source, in this repository. The [full roadmap](https://github.com/srpadmanabhuni/agentest/blob/main/docs/ROADMAP.md) has the detail; it is a plan, not a commitment.

- [x] Rule engine with 130 executable checks, deterministic and offline
- [x] The 110-test checklist dataset on [Hugging Face](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110)
- [x] Validation method: blind, label-locked evaluation ([how it works](https://github.com/srpadmanabhuni/agentest/blob/main/docs/HOW-IT-WORKS.md))
- [x] CI gate (`--strict`, JUnit and SARIF output) and a no-install Colab and browser demo
- [x] LangGraph importer and a worked example
- [ ] More framework adapters: CrewAI, AutoGen, OpenAI Agents SDK and n8n
- [ ] Extension packs: multi-agent, privacy, red teaming, bias, explainability and data lineage
- [ ] PyPI release of `agentest-ai`

Want to build one? See [Contribute](#contribute) and [Help own a check family](#help-own-a-check-family).

## Learn more

| I want to | Go to |
|---|---|
| Understand it in ten minutes | [Why agentest: developers](https://github.com/srpadmanabhuni/agentest/blob/main/docs/guides/WHY-AGENTEST-FOR-DEVELOPERS.md), [testers](https://github.com/srpadmanabhuni/agentest/blob/main/docs/guides/WHY-AGENTEST-FOR-TESTERS.md) |
| See a full bug-detection story | [Demo: trace, failed check, evidence, corrected result](https://github.com/srpadmanabhuni/agentest/blob/main/docs/demos/BUG-DETECTION-DEMO.md) |
| Walk through real failures | [Walkthroughs](https://github.com/srpadmanabhuni/agentest/blob/main/docs/walkthroughs/README.md) |
| Install, CLI, config, CI | [Getting started](https://github.com/srpadmanabhuni/agentest/blob/main/docs/GETTING-STARTED.md), [User Guide](https://github.com/srpadmanabhuni/agentest/blob/main/docs/USER-GUIDE.md), [CI](https://github.com/srpadmanabhuni/agentest/blob/main/docs/developers/CI.md) |
| Read a report | [Reading the report](https://github.com/srpadmanabhuni/agentest/blob/main/docs/READING-THE-REPORT.md) |
| See every document | [Documentation index](https://github.com/srpadmanabhuni/agentest/blob/main/docs/README.md), [FAQ](https://github.com/srpadmanabhuni/agentest/blob/main/docs/FAQ.md) |
| Know how it works and where it stops | [How it works and coverage](https://github.com/srpadmanabhuni/agentest/blob/main/docs/HOW-IT-WORKS.md), [Roadmap](https://github.com/srpadmanabhuni/agentest/blob/main/docs/ROADMAP.md) |
| Browse the checklist | [Hugging Face dataset](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110), [how GitHub and HF fit together](https://github.com/srpadmanabhuni/agentest/blob/main/docs/CATALOGUE-AND-HF.md) |

## Contribute

You do not need to be an agent expert. Pick a [`good first issue`](https://github.com/srpadmanabhuni/agentest/labels/good%20first%20issue), follow [the ten-minute first pull request](https://github.com/srpadmanabhuni/agentest/blob/main/CONTRIBUTING.md#your-first-pull-request-in-about-ten-minutes), or bring a redacted agent trace to [Discussions](https://github.com/srpadmanabhuni/agentest/discussions). Theme: *Bring an agent trace, contribute a test.* Wrong verdict? Use the [issue forms](https://github.com/srpadmanabhuni/agentest/issues/new/choose). Please follow the [Code of Conduct](https://github.com/srpadmanabhuni/agentest/blob/main/CODE_OF_CONDUCT.md). New to open source? Open the repo in a [GitHub Codespace](https://codespaces.new/srpadmanabhuni/agentest) (set up for you) and join [contributor week, 23–30 Nov 2026](https://github.com/srpadmanabhuni/agentest/discussions/100). We reply within 24 hours and review within 48 hours ([how we work](https://github.com/srpadmanabhuni/agentest/blob/main/CONTRIBUTING.md#response-promise)).

## Contributors

AiEnsured agentest, an Agentic AI Testing platform, grows through the people who enhance and contribute. It is unique and relevant for responsible and safe AI agents because it checks what the agent actually did, not only what it said ([why, with sources](https://github.com/srpadmanabhuni/agentest/blob/main/docs/START_HERE.md#what-makes-agentest-different)). Thank you to everyone below whose pull request is merged.

<!-- CONTRIBUTORS:START -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="33.33%"><a href="https://github.com/Neeraj111010"><img src="https://github.com/Neeraj111010.png?size=100" width="100px;" alt="Neeraj111010"/><br /><sub><b>Neeraj111010</b></sub></a><br /><a href="https://github.com/srpadmanabhuni/agentest/pull/68" title="Hindi titles for five checklist rows">🌐 📖</a></td>
      <td align="center" valign="top" width="33.33%"><a href="https://github.com/CyberKun"><img src="https://github.com/CyberKun.png?size=100" width="100px;" alt="CyberKun"/><br /><sub><b>CyberKun</b></sub></a><br /><a href="https://github.com/srpadmanabhuni/agentest/pull/106" title="class selection in std run --ids and a minimal CI gate (#107)">💻 📖</a></td>
    </tr>
  </tbody>
</table>
<!-- CONTRIBUTORS:END -->

Key: 💻 code, ⚠️ tests, 📖 docs, 🌐 translation. Each badge links the merged pull request. The same list is in [CONTRIBUTORS.md](https://github.com/srpadmanabhuni/agentest/blob/main/CONTRIBUTORS.md). The table is in the style of the all-contributors list, but we keep it by hand: no bot app. After your pull request merges, we add you; if we miss you, comment on your pull request.

[agentest contributor week, 23–30 Nov 2026](https://github.com/srpadmanabhuni/agentest/discussions/100) is the next push: ten starter issues, public credit and a leaderboard of merged pull requests. There is no money and there are no prizes.

## Help own a check family

We are looking for co-maintainers, one per area:

- **Extension families:** red teaming, privacy, bias, explainability, data lineage and multi-agent.
- **Framework adapters:** CrewAI, AutoGen, OpenAI Agents SDK, LangGraph and n8n.

To volunteer, comment on the [contributor week Discussion](https://github.com/srpadmanabhuni/agentest/discussions/100). What an owner does is in [CONTRIBUTING.md](https://github.com/srpadmanabhuni/agentest/blob/main/CONTRIBUTING.md#help-own-a-check-family).

## Author, citation, licence

By Dr Srinivas Padmanabhuni, CTO and Co-founder, AiEnsured (testAIng.com). Contact: srinivas AT testAIng.com. Cite with DOI [10.5281/zenodo.23597877](https://doi.org/10.5281/zenodo.23597877) (all versions) or [`CITATION.cff`](https://github.com/srpadmanabhuni/agentest/blob/main/CITATION.cff); details in [About](https://github.com/srpadmanabhuni/agentest/blob/main/docs/ABOUT.md). Runner: Apache-2.0 ([LICENSE](https://github.com/srpadmanabhuni/agentest/blob/main/LICENSE)); checklist data: CC BY 4.0. Catalogue: pinned catalogue **v1.3.1** ([`catalog/VERSION`](https://github.com/srpadmanabhuni/agentest/blob/main/catalog/VERSION)). Selected [references](https://github.com/srpadmanabhuni/agentest/blob/main/docs/READING-LIST.md); [release highlights](https://github.com/srpadmanabhuni/agentest/blob/main/docs/RELEASE-HIGHLIGHTS.md).
