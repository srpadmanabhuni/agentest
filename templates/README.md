# Templates

Copy-and-adapt starting points for checking your own agent's recorded traces.

| File | What it does |
|---|---|
| [`test_langgraph.py`](test_langgraph.py) | pytest template: imports recorded LangGraph message-list episodes (dialect `langgraph_msgs`) and runs the checks in-process with `agentest.run` and `agentest.assert_passes`. Every check must report `pass`, `fail` or `n/a`, and the check IDs you list must pass. |
| [`regression.yaml`](regression.yaml) | Config for a regression suite: graduated check IDs, run with `--ids` and `--strict` so CI exits 1 on a fail. |
| [`capability.yaml`](capability.yaml) | Config for a capability suite: report only (no `--strict`). A low pass rate is expected. |

Guide: [Capability suites and regression suites](../docs/guides/CAPABILITY-AND-REGRESSION-SUITES.md).

Run it from a clone against the recorded example in [`examples/langgraph_import/`](../examples/langgraph_import/):

```bash
pip install -e ".[dev]"
python -m pytest -q templates/test_langgraph.py
```

In your own repository, copy `test_langgraph.py` into `tests/` and set `AGENTEST_LG_NATIVE`, `AGENTEST_LG_MAP`,
`AGENTEST_LG_TOOLS`, `AGENTEST_LG_CARD`, `AGENTEST_LG_SERVICE` and `AGENTEST_LG_MUST_PASS` (see the file header).
Offline: no model, no network, no new dependency. Full guide: [docs/integrations/langgraph.md](../docs/integrations/langgraph.md).

LangGraph is the single flagship framework template for now.
