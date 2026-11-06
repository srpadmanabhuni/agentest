# Tester quickstart

`agentest-ai` is not on PyPI. The copy-paste path is a clone. GitHub renders the files. A separate docs site is not required.

```bash
git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git
cd agentest
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python examples/colab_quickstart.py
```

PyYAML is the only required package. No API key, GPU, or model. The script prints a failing refill agent, one temporary repair, and the rerun. It does not change the shipped traces and it does not report a pass rate.

- Notebook: [examples/colab_quickstart.ipynb](../../examples/colab_quickstart.ipynb). Colab (file on the default branch): <https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/examples/colab_quickstart.ipynb>
- Walkthroughs of single checks: [docs/walkthroughs](../walkthroughs/README.md).
- Catalogue on Hugging Face, live default config `all`: [agentic-ai-test-checklist-110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110).
- Plain OpenTelemetry trace, standard library only: [examples/otel_plain/emit_trace.py](../../examples/otel_plain/emit_trace.py).
- JUnit in CI: [CI integration](../developers/CI.md).
- Contribute a trace: [CONTRIBUTING.md](../../CONTRIBUTING.md).

The block below installs the tagged CLI `v3.3.2`. That tag does not contain files added after it. `agentest-ai` is still not a live PyPI package.

```bash
python -m venv .venv && . .venv/bin/activate
# pip install agentest-ai   (PyPI: pending, not live yet; until then use the git line below)
pip install "agentest-ai @ git+https://github.com/srpadmanabhuni/agentest@v3.3.2"
agentest version                                   # 3.3.2
agentest std validate                              # the bundled agents' AgentCards and MCP tools are valid
agentest std run --mode strict                     # 130 IDs x bundled agents, rules + harness verdicts only
agentest std run --agent a62 --format md           # one agent, as a Markdown table
agentest std catalog --format csv --out catalog.csv
```

Judge your own agent's traces (any OTLP/JSON export):

```bash
agentest std run --otlp traces.json --card agent-card.json --tools tools.json --format html --out report.html
```

Next: [reading results](READING-RESULTS.md), the [per-test guide](PER-TEST-GUIDE.md) and
[risk-based planning](TEST-PLANNING.md).
