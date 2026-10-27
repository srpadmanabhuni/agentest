# CI integration

agentest runs offline, needs no secrets and costs nothing. Record traces in your pipeline (or commit them), then:

```yaml
# .github/workflows/agentest.yml
name: agent assurance
on: [push, pull_request]
jobs:
  agentest:
    runs-on: ubuntu-latest
    permissions: {contents: read, security-events: write}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install "agentest @ git+https://github.com/srpadmanabhuni/agentest@v3.0.0"
      # 1. produce traces: run your agent's test inputs with OTel export to a file (see INSTRUMENTING.md)
      - run: python run_agent_tests.py --otlp-out traces.jsonl
      # 2. judge them
      - run: agentest std run --otlp traces.jsonl --card agent-card.json --tools tools.json --mode strict --format sarif --out agentest.sarif
      - run: agentest std run --otlp traces.jsonl --card agent-card.json --tools tools.json --mode strict --format junit --out agentest.xml --strict
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with: {sarif_file: agentest.sarif}
```

- `--strict` makes the job fail on any fail verdict. To gate on P0 only, disable the rest in a config file
  (`disable: [...]`) or join the versioned JSON `results[]` with `agentest std catalog --format csv` (column `priority`).
- **Instrumentation-coverage gate (v3.5):** `std run` exits 1 when an agent's share of `n/a` + `not-run` verdicts
  is above `max_na_share` (default 0.90): its traces carry too little standard instrumentation for the checks to say
  anything. IDs disabled by config are left out; `not-assessed` (no judge) is reported apart and never counts. Set
  `--max-na 0.75` or `thresholds: {max_na_share: 0.75}` in the config (`1` turns it off). The JSON report has a
  `coverage` block, JUnit suites carry `agentest.coverage.*` properties plus one failing
  `agentest/instrumentation-coverage` test case per agent over the threshold, and SARIF has a rule of the same id
  with an error result per such agent (full report in `runs[0].properties.instrumentationCoverage`). The console
  line names the trace signals that were missing (tool spans, token usage, state changes ...).
- JUnit output works with any CI that reads JUnit (GitLab, Jenkins, Azure DevOps, CircleCI).
- SARIF works with any SARIF viewer; uploading to GitHub code scanning is optional.

## The repository's own CI

`.github/workflows/ci.yml` runs ruff, `pytest` (including the agent-independence, no-lock-in and doc-link tests),
the catalogue pin check, the regression floors and a fresh install.
