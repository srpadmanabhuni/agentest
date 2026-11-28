# GitHub Action and pre-commit hook

AiEnsured agentest, an Agentic AI Testing platform, checks what your agent actually did (from its recorded traces), not only what it said. This page shows the two shortest ways to run it on every change:

- **GitHub Action**: one `uses:` step in a workflow. It fails the job when any check fails.
- **GitHub Action from PyPI** ([srpadmanabhuni/agentest-action](https://github.com/srpadmanabhuni/agentest-action)): a standalone composite action that installs the `agentest-ai` release from PyPI. Use `srpadmanabhuni/agentest-action@v1` with `otlp: traces/*.otlp.jsonl`. It takes the same inputs as the in-repo action below, plus `version` to pin a PyPI release.
- **pre-commit hook**: runs the same checks before a commit that changes trace files or agent folders.

Both run offline. They make no model calls and need no API keys, secrets or network access beyond installing agentest.

> **Install note.** The action installs agentest from the same ref of this repository that you pin in `uses:`, and pre-commit installs it from the `rev:` you pin. Neither needs PyPI. For a local or CI CLI install, use the command below. Pin the action to a tag such as `v3.5.1` or to a commit SHA.
>
> ```bash
> pip install agentest-ai
> ```

## GitHub Action in 2 minutes

1. Commit your recorded OpenTelemetry GenAI traces (see [INSTRUMENTING.md](INSTRUMENTING.md)), for example `traces/run.otlp.jsonl`, with an optional A2A AgentCard and MCP tools list.
2. Save this as `.github/workflows/agentest.yml` using the [Marketplace action](https://github.com/marketplace/actions/agentest-agentic-evals) (`srpadmanabhuni/agentest-action@v1`, or pin `srpadmanabhuni/agentest@<sha>` directly):

```yaml
name: agentest
on: [push, pull_request]
permissions: {contents: read}
jobs:
  agentest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: srpadmanabhuni/agentest-action@v1
        with:
          otlp: traces/*.otlp.jsonl
```

3. Push. The step fails when any check returns `fail`, and the job summary shows the totals and the Markdown report.

A fuller example, with agent folders, a JUnit report and an artifact upload, is in [examples/integrations/github-action.yml](../../examples/integrations/github-action.yml).

### Inputs

| Input | Default | What it does |
|---|---|---|
| `otlp` | empty | OTLP trace files or globs (`.json`, `.jsonl`, `.pb`), separated by spaces or new lines. Empty judges agent folders instead. |
| `card`, `tools` | empty | With `otlp`: an A2A AgentCard JSON and an MCP `tools/list` JSON. |
| `agents` | `agents` | Without `otlp`: the folder of agent folders (`agent-card.json`, `tools.json`, `traces/`). |
| `agent` | empty | Without `otlp`: judge one agent folder only. |
| `ids` | empty | Limit the report to IDs or classes, for example `T5,T6-002`. |
| `mode` | CLI default | `strict` (standard OTel/A2A/MCP fields only) or `examples`. |
| `config` | empty | YAML/JSON config (disable IDs, thresholds, `rules_dir`, scenarios). |
| `format` | `md` | Report format: `md`, `json`, `junit`, `sarif`, `html` or `csv`. |
| `report` | `agentest-report.<ext>` | Report file path. |
| `fail-on-fail` | `true` | `true` fails the step on any fail verdict (`--strict`); `false` only reports. |
| `job-summary` | `true` | Add the totals (and the report, for `md`) to the job summary. |
| `pr-comment` | `false` | Off by default. `true` posts, or updates in place, one pull request comment listing the failed check IDs with evidence; `summary` writes only the job summary. See [GITHUB-ACTION-PR-COMMENT.md](GITHUB-ACTION-PR-COMMENT.md). |
| `github-token`, `comment-key`, `pr-number`, `github-api-url` | workflow token, `agentest`, from the event, `github.api_url` | Only used with `pr-comment: true`; see [GITHUB-ACTION-PR-COMMENT.md](GITHUB-ACTION-PR-COMMENT.md). |
| `python-version` | `3.12` | Python to set up; empty uses the runner's Python (3.11 or later). |
| `install` | empty | Empty installs agentest from the action's own ref. Otherwise any pip requirement, for example `agentest-ai @ git+https://github.com/srpadmanabhuni/agentest@<sha>`. |

### Outputs

`exit-code` (0 = no fail, 1 = at least one fail, 2 = bad input), `passed`, `failed`, `not-applicable` and `report`, plus `comment-status` and `comment-url` when `pr-comment` is used.

### What the step runs

The action runs `agentest std run` with the inputs above, so you can reproduce any CI result locally:

```shell
agentest std run --otlp traces/run.otlp.jsonl --card agent-card.json --tools tools.json --format md --out agentest-report.md --strict
```

Inputs reach the shell only as environment variables and are never run as code. A pattern that matches no file stops the step with exit code 2, so a wrong path never passes silently.

### SARIF for code scanning

```yaml
      - uses: srpadmanabhuni/agentest@<sha>
        with:
          otlp: traces/*.otlp.jsonl
          format: sarif
          report: agentest.sarif
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with: {sarif_file: agentest.sarif}
```

Uploading SARIF needs `permissions: {contents: read, security-events: write}` on the job.

## pre-commit hook

Add this to `.pre-commit-config.yaml` in your repository, replacing `<sha>` with a commit SHA of this repository:

```yaml
repos:
  - repo: https://github.com/srpadmanabhuni/agentest
    rev: <sha>
    hooks:
      - id: agentest-otlp        # judge the staged *.otlp.json / *.otlp.jsonl / *.otlp.pb files
        args: [--card, agent-card.json, --tools, tools.json, --otlp]
      # - id: agentest-agents    # or: judge every folder under agents/ when one changes
      # - id: agentest-validate  # and: check the agent folders are well formed
```

Then run `pre-commit install` once. A copy of this file is in [examples/integrations/pre-commit-config.yaml](../../examples/integrations/pre-commit-config.yaml).

| Hook id | Runs | When |
|---|---|---|
| `agentest-otlp` | `agentest std run --strict --otlp <staged files>` | a staged file ends in `.otlp.json`, `.otlp.jsonl` or `.otlp.pb` |
| `agentest-agents` | `agentest std run --strict --agents agents` | an AgentCard, tools list or trace file changes |
| `agentest-validate` | `agentest std validate --agents agents` | the same files change |

- For `agentest-otlp`, keep `--otlp` last in `args`, because pre-commit adds the staged file names after the args. Pass `--card` and `--tools` when you have them: without them, the checks that compare the trace with the declared tools and allowed hosts have less to go on, and some verdicts differ.
- For another agents folder, set `args: [--agents, path/to/agents]` on `agentest-agents` or `agentest-validate`.
- Try a hook before you commit: `pre-commit run agentest-otlp --all-files`.

## How this repository tests them

- `tests/test_github_action.py` runs the action's script (`scripts/gh_action_run.sh`) on the bundled demo agents: the good agent passes, the buggy one fails the step, report-only mode exits 0, and missing files or unsafe input stop with exit code 2. It also runs each pre-commit hook's exact command.
- The `action-self-test` CI job runs the action itself with `uses: ./` on the demo agents, and the pre-commit hooks with `pre-commit try-repo`.

## Enhance and contribute

Want another input, a GitLab CI template or a hook for another trace format? Open an issue or a pull request: see [CONTRIBUTING.md](../../CONTRIBUTING.md) and the [good first issues](https://github.com/srpadmanabhuni/agentest/contribute).
