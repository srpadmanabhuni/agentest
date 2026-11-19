# Quickstart

**Install from PyPI** (Python 3.11+, no API key, no model). The package name is `agentest-ai`; the import and the `agentest` command stay `agentest`. Package page: https://pypi.org/project/agentest-ai/.

```bash
pip install agentest-ai
agentest std run --agent a22 --ids T1-018 --format md
```

Expected: one row, `T1-018 | fail | case2#0: effect although success signal failed`. The bundled shopping agent told the user a charger "has been added to the cart" while the cart was empty (a recorded run; nothing was bought). This is the case in the [agent failure report](AGENT-FAILURE-REPORT.md), section 4. The bundled sample agents ship with the package, so that command does not need a clone. How to read `pass` / `fail` / `n/a`: [Reading the report](READING-THE-REPORT.md).

**From source**, if you want the examples folder as a clone:

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git && cd agentest
python3 -m venv .venv && . .venv/bin/activate && pip install -q -e .
agentest std run --agent a22 --ids T1-018 --format md
```

No-install options: the [Assurance Report Card](CATALOGUE-AND-HF.md) (paste or upload a trace) or the [Colab notebook](../examples/colab_quickstart.ipynb).

Other guides for the same first run, with more detail:

- [Start here](START_HERE.md): what an agent test is, how to read the result, and how to point agentest at your own agent.
- [Install and quickstart, all the ways](INSTALL-AND-QUICKSTART.md): every install option, including Docker and a pinned git install.
- [Tester quickstart](testers/QUICKSTART.md): the tester path, including the Colab walkthrough.
- [Getting started](GETTING-STARTED.md): six steps from install to a CI gate.
- [New tests](new-tests/README.md): opt-in checks `NT-001` to `NT-030` (`agentest std run --ids NT`).
- [Challenge](CHALLENGE.md): the public first-run page, including gaps where checks still miss.
