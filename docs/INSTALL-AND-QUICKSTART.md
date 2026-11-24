# Install and quickstart (all the ways)

The path from install to a first verdict is [Start here](START_HERE.md#the-path). This page lists other ways to install. It does not replace that path. The shopping-agent check on the same install is the [Quickstart](QUICKSTART.md).

The [README](../README.md) has the 60-second first win. This page holds every other way to install and run agentest.

Python 3.11 or newer. The package name on PyPI is `agentest-ai`; the import and the `agentest` command stay `agentest`. Install and judge a bundled sample agent:

```bash
pip install agentest-ai
agentest std run --agent a14
```

To work from a clone (needed for the `examples/` folder), one command installs that checkout into a new virtualenv and judges `a14`. `--quiet` and `pip install -q` hide clone and pip progress.

```bash
git clone --depth 1 --quiet https://github.com/srpadmanabhuni/agentest.git && cd agentest && python3 -m venv .venv && . .venv/bin/activate && python -m pip install -q -e . && agentest std run --agent a14
```

![Terminal recording of the one-command quickstart: clone agentest, install the checkout into a new virtualenv, and run agentest std run --agent a14](assets/quickstart.gif)



## Quickstart from a clone (copy and paste)

The command above installs the `agentest` CLI from this checkout. The script below is the refill-agent walkthrough and needs only PyYAML.

This walkthrough uses the clone so it can see `examples/`. Python 3.11+, no API key, no GPU, no model.
The only required package is PyYAML (`requirements.txt`). For the CLI alone, `pip install agentest-ai` is enough.

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
pip install agentest-ai
# or from git: pip install git+https://github.com/srpadmanabhuni/agentest
agentest std run --agent a14                                   # one bundled sample agent's recorded traces
agentest std run --agent a14 --format html --out report.html   # html, json, junit, sarif, md, csv
```

Every bundled agent ships with its OpenTelemetry traces, so judging needs no API key, network or model.
The examples folder used above is in the git clone, not in that install.
Next: your own traces (`agentest std run --otlp my_traces.otlp.jsonl`), the [Quickstart](#quickstart) below,
or [contribute](../CONTRIBUTING.md).

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

A PyPI install provides the `agentest` command without the examples folder. A clone is needed for the walkthroughs below.
agentest ships 165 tests, grouped into 4 pillars in [docs/FRAMEWORK.md](FRAMEWORK.md). The published catalogue is the [Agentic AI Test Checklist 110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110).


## Install

```bash
pip install agentest-ai
agentest version     # 3.5.1
```

Or from a fresh clone:

```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest && pip install -e ".[dev]"
```
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

The HTML report for the seeded-defect demo agent `refill_bot_buggy` (top rows; the full report lists every ID in that run):

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

## With Docker (build locally)

No Python setup on your machine. Build from a clone; no image is published to a registry yet.

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git && cd agentest
docker build -t agentest .
docker run --rm agentest
```

The default command reproduces the README demo and prints `T1-018 | fail | case2#0: claims success`. To judge your own trace, mount it and pass any `agentest` arguments:

```bash
docker run --rm -v "$PWD/traces:/traces" agentest std run --otlp /traces/my_trace.otlp.json --format md
```

