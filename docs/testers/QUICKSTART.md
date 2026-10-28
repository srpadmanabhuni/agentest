# Tester quickstart

```bash
python -m venv .venv && . .venv/bin/activate
pip install "agentest @ git+https://github.com/srpadmanabhuni/agentest@v3.0.0"
agentest version                                   # 3.0.0
agentest std validate                              # the bundled agents' AgentCards and MCP tools are valid
agentest std run --mode strict                     # 136 IDs x bundled agents, rules + harness verdicts only
agentest std run --agent a62 --format md           # one agent, as a Markdown table
agentest std catalog --format csv --out catalog.csv
```

Judge your own agent's traces (any OTLP/JSON export):

```bash
agentest std run --otlp traces.json --card agent-card.json --tools tools.json --format html --out report.html
```

Next: [reading results](READING-RESULTS.md), the [per-test guide](PER-TEST-GUIDE.md) and
[risk-based planning](TEST-PLANNING.md).
