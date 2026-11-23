# Scheduled runs

Do [Start here](../START_HERE.md#the-path) first. This page runs that same judge on a schedule. It does not add another install.

Record traces in your repository (or produce them in an earlier job), then run agentest on those files and upload the SARIF report. The judge command is step 3 of the path, with `--format sarif`.

The workflow file to copy is [`examples/integrations/github-actions-cron.yml`](../../examples/integrations/github-actions-cron.yml). Save it as `.github/workflows/agentest-scheduled.yml` in your repository. It expects recorded traces at `traces/*.otlp.jsonl`.

```yaml
name: agentest-scheduled

on:
  schedule:
    - cron: "0 6 * * 1"
  workflow_dispatch:

permissions:
  contents: read
  security-events: write

jobs:
  judge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install
        run: python -m pip install agentest-ai
      - name: Judge recorded traces
        run: agentest std run --otlp traces/*.otlp.jsonl --format sarif --out agentest.sarif
      - name: Upload SARIF
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: agentest.sarif
```

The install step is the install from [the path](../START_HERE.md#the-path). The judge step is `agentest std run --otlp` from that path, writing SARIF. `workflow_dispatch` lets you run the same job once, without waiting for the cron.

`--format sarif` and the upload action are the same pair as the [CI guide](../developers/CI.md#sarif-and-junit-reports). A pull-request gate, rather than a schedule, is [tutorial 4](../tutorials/04-ci-cd-github-actions.md).

GitHub code scanning must be enabled on the repository before the upload step can attach results. The SARIF file is still written when uploading is skipped.
