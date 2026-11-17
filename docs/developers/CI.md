# CI integration

agentest runs offline, needs no secrets and costs nothing. Record traces in your pipeline (or commit them), then:

**Shortest path:** the composite GitHub Action (`uses: srpadmanabhuni/agentest@<sha>`) and the pre-commit hooks in [GITHUB-ACTION.md](GITHUB-ACTION.md). The workflows below do the same with plain `pip` and `agentest` steps.

## Minimal gate

Save this as `.github/workflows/agentest.yml`; replace `my_agent` with your agent folder under `agents/`, containing `agent-card.json`, `tools.json`, and recorded traces in `traces/`.

```yaml
name: agent-gate
on: [push, pull_request]
permissions: {contents: read}
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: python -m pip install "git+https://github.com/srpadmanabhuni/agentest@v3.4.0"
      - run: agentest std run --agents agents --agent my_agent --mode strict --strict
```

`--strict` returns exit code 1 when any check fails, making the step and job fail; it returns 0 when no check fails (which may include `n/a` verdicts).
For saved reports and a run summary, use the [full gate workflow](../../examples/integrations/github-actions-gate.yml) and [tutorial 4](../tutorials/04-ci-cd-github-actions.md).

## SARIF and JUnit reports

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
      # pip install agentest-ai   (PyPI: pending, not live yet; until then use the git line below)
      - run: pip install "agentest-ai @ git+https://github.com/srpadmanabhuni/agentest@v3.4.0"
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
- JUnit output works with any CI that reads JUnit (GitLab, Jenkins, Azure DevOps, CircleCI).
- SARIF works with any SARIF viewer; uploading to GitHub code scanning is optional.

## The repository's own CI

`.github/workflows/ci.yml` runs ruff, `pytest` (including the agent-independence, no-lock-in and doc-link tests),
the catalogue pin check, the regression floors and a fresh install.
