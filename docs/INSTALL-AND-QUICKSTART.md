# Install and quickstart (all the ways)

The path from install to a first verdict is [Start here](START_HERE.md#the-path). This page lists other ways to install. It does not replace that path. The shopping-agent check on the same install is the [Quickstart](QUICKSTART.md).

The [README](../README.md) has the 60-second path: `pip install agentest-ai`, `agentest demo`, then judge your own agent. This page holds every other way to install and run agentest, including the clone-based quickstarts that used to be in the README.

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
Next: the sample trace that ships in the clone (`agentest std run --otlp examples/first_trace/trace.otlp.json --tools examples/first_trace/tools.json --format md`; swap in your own trace file), the [Quickstart](#quickstart) below,
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
agentest version     # 3.8.0
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
agentest std run --otlp examples/first_trace/trace.otlp.json --tools examples/first_trace/tools.json --format md
agentest std run                                            # all 113 bundled agents (98 reference + 15 samples)
agentest std run --format junit --out agentest.xml --strict # CI gate (also json, sarif, html, md, csv)
```

Swap in your own trace file.

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

The default command reproduces the README demo and prints `T1-018 | fail | case2#0: claims success`. To judge the sample trace that ships in the clone:

```bash
docker run --rm -v "$PWD/examples/first_trace:/traces" agentest std run --otlp /traces/trace.otlp.json --tools /traces/tools.json --format md
```

Swap in your own trace file.

## Clone quickstart: the shopping agent a22

The path from install to a first verdict is [Start here](https://github.com/srpadmanabhuni/agentest/blob/main/docs/START_HERE.md#the-path). The blocks below are that install, then the shopping-agent check. They are not a second install.

**Install from PyPI** (Python 3.11+, no API key, no model). The package name is `agentest-ai`; the import and the `agentest` command stay `agentest`:

```bash
pip install agentest-ai
```

```bash
agentest --help
```

Package page: https://pypi.org/project/agentest-ai/

To run the latest unreleased code instead:

```bash
pip install git+https://github.com/srpadmanabhuni/agentest
```

Then run a bundled example use case and read the markdown report.

1. **Install** from PyPI, from GitHub, or from a clone of this repository.
2. **Run** a bundled example use case — a shopping agent that said it added an item to the cart when the cart was empty (the clip above).
3. **Read the report** — one markdown row naming the check, the verdict and the evidence.

**From a clone, three lines** (Python 3.11+, no API key, no model). This reproduces the run in the clip above and includes the examples folder:

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git && cd agentest
python3 -m venv .venv && . .venv/bin/activate && pip install -q -e .
agentest std run --agent a22 --ids T1-018 --format md
```

Expected: one row, `T1-018 | fail | case2#0: claims success`. Releases up to 3.5.1 print the same fail with the older detail `effect although success signal failed`, as in this real output from a clean virtualenv after installing agentest-ai 3.5.0 from PyPI (package page: https://pypi.org/project/agentest-ai/):

```text
# agentest 3.5.0 report (examples mode)

0 pass, 1 fail, 0 n/a over 1 agent(s).

## Bundled buggy agent from a clone

A longer run, from the same clone as the [clone quickstart](#clone-quickstart-the-shopping-agent-a22). This runs agentest on a bundled sample agent that has seeded bugs and checks four things at once:

```bash
agentest std run --agents examples/agnostic_demo/agents --agent refill_bot_buggy \
  --ids T1-018,T2-001,T4-003,T7-014 --format md
```

It prints a caught-bug report: one line of evidence per failed check.

![Four failed checks on the buggy sample agent. T1-018: claims success. T2-001: place_refill before verify_identity. T4-003: injected recipient audit@evil.example. T7-014: unmasked email.](https://raw.githubusercontent.com/srpadmanabhuni/agentest/main/docs/img/caught-bug.png)

*A rendering of the real output, with a plain-English label added per check. The evidence text is verbatim (T2-001 shortened); the plain `--format md` output is a table of the same rows.*

For contrast, the clean sibling agent passes everything it can be judged on: `agentest std run --agents examples/agnostic_demo/agents --agent refill_bot` prints `refill_bot: 55 pass, 0 fail`. The same before-and-after walkthrough is in the [Colab](https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/examples/colab_quickstart.ipynb) above, or run `python examples/colab_quickstart.py` from the clone.
