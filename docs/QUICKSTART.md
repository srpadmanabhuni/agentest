# Quickstart

The path from install to a first verdict is [Start here](START_HERE.md#the-path). This page does not add another install. It is the shopping-agent check from the [README quickstart](../README.md#quickstart), on that same install.

```bash
pip install agentest-ai
```

```bash
agentest std run --agent a22 --ids T1-018 --format md
```

Expected: one row, `T1-018 | fail | case2#0: claims success`. How to read `pass` / `fail` / `n/a`: [Reading the report](READING-THE-REPORT.md).

A checkout that includes the examples folder: [Install and quickstart](INSTALL-AND-QUICKSTART.md#quickstart-from-a-clone-copy-and-paste).

No-install options: the [Assurance Report Card](CATALOGUE-AND-HF.md) (paste or upload a trace) or the [Colab notebook](../examples/colab_quickstart.ipynb).

Other guides that continue from the same path:

- [Start here](START_HERE.md#the-path): install, run the demo, then judge your own trace.
- [Install and quickstart, all the ways](INSTALL-AND-QUICKSTART.md): other install options, including Docker and a pinned git install.
- [Tester quickstart](testers/QUICKSTART.md): the tester path, including the Colab walkthrough.
- [Getting started](GETTING-STARTED.md): six steps from that path to a CI gate.
- [New tests](new-tests/README.md): opt-in checks (`agentest std run --ids NT`).
