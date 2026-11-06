# Tester quickstart

The install below is the `v3.3.2` tag (PyPI is not live yet). The notebook and the walkthroughs are files in the git repository. GitHub renders them. A separate docs site is not required.

- Notebook, free CPU, no login and no model: [examples/colab_quickstart.ipynb](../../examples/colab_quickstart.ipynb). From a clone: `python examples/colab_quickstart.py`.
- Walkthroughs of single checks: [docs/walkthroughs](../walkthroughs/README.md).
- Catalogue on Hugging Face, live default config `all`: [agentic-ai-test-checklist-110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110).
- Plain OpenTelemetry trace, standard library only: [examples/otel_plain/emit_trace.py](../../examples/otel_plain/emit_trace.py).
- JUnit in CI: [CI integration](../developers/CI.md).

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
