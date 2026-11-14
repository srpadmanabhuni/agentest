# Templates

Copy-and-adapt starting points for checking your own agent's recorded traces.

| File | What it does |
|---|---|
| [`test_langgraph.py`](test_langgraph.py) | pytest template: imports recorded LangGraph message-list episodes (`agentest std import`, dialect `langgraph_msgs`), runs the checks on the imported traces, and asserts that every check reports `pass`, `fail` or `n/a` and that the check IDs you list pass. |

Run it from a clone against the synthetic example in [`examples/langgraph_import/`](../examples/langgraph_import/):

```bash
pip install -e ".[dev]"
python -m pytest -q templates/test_langgraph.py
```

In your own repository, copy `test_langgraph.py` into `tests/` and set `AGENTEST_LG_NATIVE`, `AGENTEST_LG_MAP`,
`AGENTEST_LG_TOOLS`, `AGENTEST_LG_CARD`, `AGENTEST_LG_SERVICE` and `AGENTEST_LG_MUST_PASS` (see the file header).
Offline: no model, no network, no new dependency. Full guide: [docs/integrations/langgraph.md](../docs/integrations/langgraph.md).

LangGraph is the single flagship framework template for now.
