# Install and quickstart (all the ways)

The [README](../README.md) has the 60-second first win. This page holds every other way to install and run agentest, moved here from the old README. `agentest-ai` is not on PyPI yet; all installs come from GitHub.


Python 3.11 or newer. One command clones this repo, installs that checkout into a new virtualenv, and judges the bundled agent `a14`. `--quiet` and `pip install -q` hide clone and pip progress. The project name in `pyproject.toml` is `agentest-ai`. That distribution is not published on PyPI, so `pip install agentest-ai` does not install it.

```bash
git clone --depth 1 --quiet https://github.com/srpadmanabhuni/agentest.git && cd agentest && python3 -m venv .venv && . .venv/bin/activate && python -m pip install -q -e . && agentest std run --agent a14
```

![Terminal recording of the one-command quickstart: clone agentest, install the checkout into a new virtualenv, and run agentest std run --agent a14](assets/quickstart.gif)

If agentest catches a bug for you, a ⭐ helps others find it.


## Quickstart from a clone (copy and paste)

The command above installs the `agentest` CLI from this checkout. The script below is the refill-agent walkthrough and needs only PyYAML.

`agentest-ai` is **not** on PyPI. Do not run `pip install agentest-ai`. Python 3.11+, no API key, no GPU, no model.
The only required package is PyYAML (`requirements.txt`).

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git
cd agentest
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python examples/colab_quickstart.py
```

That script judges the shipped buggy refill agent, prints the failing checks with evidence, applies one temporary
repair (identity verification before the dependent calls), and reruns. The shipped traces are not modified.
Two checks that failed now pass. Other failures stay, and the script says so. That is not a pass rate and not certification.
`n/a` is not a pass.

The same file is the notebook: [examples/colab_quickstart.ipynb](../examples/colab_quickstart.ipynb).
Colab, after you open the file from this repository:
<https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/examples/colab_quickstart.ipynb>
(the repair section is in this file once this change is on the default branch; the comparison of the two shipped agents is already there).

Catalogue (Hugging Face, config `all`): [agentic-ai-test-checklist-110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110).
Walkthroughs: [docs/walkthroughs/](walkthroughs/README.md).
Contribute a trace: [CONTRIBUTING.md](../CONTRIBUTING.md).

## Install the command without the examples folder

```bash
pip install git+https://github.com/srpadmanabhuni/agentest     # not PyPI; the package name there will be agentest-ai and it is not published
agentest std run --agent a14                                   # one bundled sample agent's recorded traces
agentest std run --agent a14 --format html --out report.html   # html, json, junit, sarif, md, csv
```

Every bundled agent ships with its OpenTelemetry traces, so judging needs no API key, network or model.
The examples folder used above is in the git clone, not in that install.
Next: your own traces (`agentest std run --otlp my_traces.otlp.jsonl`), the [Quickstart](#quickstart) below,
or [contribute](#contribute).

Shorter write-ups of single checks are in [docs/walkthroughs/](walkthroughs/README.md). A plain OpenTelemetry trace, standard library only, is [examples/otel_plain/emit_trace.py](../examples/otel_plain/emit_trace.py). A JUnit workflow is [docs/developers/CI.md](developers/CI.md). GitHub renders these files. A separate docs site is not required.

### LangGraph flagship integration

LangGraph is the single flagship framework example. Recorded message-list episodes live in [examples/langgraph_import/](../examples/langgraph_import/) (`python examples/langgraph_import/test_langgraph.py` imports them, runs the checks, and prints a short sample report; offline, no model). How to emit OTLP/GenAI spans agentest can score: [docs/integrations/langgraph.md](integrations/langgraph.md). Theme: *Bring an agent trace, contribute a test.*

## Same clone, standards CLI

The copy-paste block above is the demo. These commands are the supported engine (`agentest std`), still with only PyYAML, offline:

```bash
python -m agentest std validate --agents examples/agnostic_demo/agents
python -m agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --ids T2-001,T2-005 --format md
python -m agentest --help
```

`agentest-ai` is not on PyPI. `pip install git+https://github.com/srpadmanabhuni/agentest` installs the `agentest` command without the examples folder.
agentest runs 130 checks: the 110 tests of the open Agentic AI Test Checklist (7 test classes, T1 to T7, grouped into
4 pillars in [docs/FRAMEWORK.md](FRAMEWORK.md)) plus 20 repo extensions (`X-001` to `X-020`); 47 of the 110 are P0.


## Install

```bash
# pip install agentest-ai   (PyPI: pending, not live yet; until then use the git line below)
pip install git+https://github.com/srpadmanabhuni/agentest   # from git, no clone
agentest version     # 3.3.2
```

or from a fresh clone: `git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest && pip install -e ".[dev]"`.
Python 3.11+, one runtime dependency (PyYAML), works offline. The catalogue and the bundled agents' standard files
ship with the package.

## Quickstart

```bash
agentest std validate --agents examples/agnostic_demo/agents
agentest std run --agents examples/agnostic_demo/agents     # refill_bot: 55 pass, 0 fail; refill_bot_buggy: 41 pass, 16 fail
agentest std run --otlp my_traces.otlp.jsonl --card agent-card.json --tools tools.json   # your own agent
agentest std run                                            # all 113 bundled agents (98 reference + 15 samples)
agentest std run --format junit --out agentest.xml --strict # CI gate (also json, sarif, html, md, csv)
```

The HTML report for the seeded-defect demo agent `refill_bot_buggy` (top rows; the full report lists all 130 IDs):

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy --format html --out report.html
```

![HTML report for refill_bot_buggy: one row per ID with pass, fail or n/a and the evidence, e.g. T1-004 fail "recipients outside fence", T2-005 fail "disclosure before verification"](img/refill_bot_buggy-html-report.png)


## Develop

```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
ruff check . && python -m pytest -q
python scripts/coverage_table.py --check
```
