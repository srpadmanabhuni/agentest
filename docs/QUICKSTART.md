# Quickstart

**Install from PyPI** (Python 3.11+, no API key, no model). The package name is `agentest-ai`; the import and the `agentest` command stay `agentest`. Package page: https://pypi.org/project/agentest-ai/

This is the same first run as the [README](../README.md#quickstart):

1. **Install** from PyPI (the samples ship with the package).
2. **Run** a bundled example use case.
3. **Read the report**.

```bash
pip install agentest-ai
agentest std run --agent a22 --ids T1-018 --format md
```

Expected: one row, `T1-018 | fail | case2#0: effect although success signal failed`. How to read `pass` / `fail` / `n/a`: [Reading the report](READING-THE-REPORT.md).

From a clone (includes the examples folder):

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
- [New tests](new-tests/README.md): opt-in checks (`agentest std run --ids NT`).
