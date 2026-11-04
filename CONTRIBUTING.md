# Contributing

Thanks for helping. Contact: Dr Srinivas Padmanabhuni, srinivas AT testAIng.com.

## Set up

```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q && ruff check src tests scripts && python scripts/check_catalog_pins.py
```

## Rules

1. One catalogue ID per PR when possible (`T1-001`, ...). Do not renumber T1-T7 IDs; repo-only checks use `X-0NN`.
2. A new or changed check must show: the ID, a passing agent and a failing agent (every ID needs both), and the threshold fixed in code.
3. Deterministic or metamorphic oracles only. No model judge in the pass/fail path and no third-party eval frameworks.
4. Regex/keyword checks over free text must be labelled as uncalibrated heuristics in their doc.
5. Cite original sources (arXiv, DOI, standards, official docs) in `src/agentest/refs.py`.
6. If rules or agents change, regenerate and commit the generated docs:
   `python scripts/gen_test_docs.py && python scripts/gen_tester_docs.py && python scripts/coverage_table.py`.
   Follow the [Author Guide](docs/AUTHOR-GUIDE.md) and its contribution checklist.
7. Catalogue changes land in the catalogue first; then update `catalog/VERSION` (`python scripts/check_catalog_pins.py --write-hashes`).
8. Add a line under `## [Unreleased]` in `CHANGELOG.md`.

## Run the tests

```bash
python -m pytest -q                       # full suite, offline, a few minutes
python -m pytest -q tests/test_framework.py         # one file
ruff check src tests scripts
```

CI runs the same commands on every pull request.

## Add a check or a test case

- **A test case for an existing check** (the most useful first PR): add a small passing and a small failing
  example (a redacted OTLP trace, plus the AgentCard / MCP tools list if the check needs them) under
  `tests/fixtures/`, and a test in `tests/` that asserts the verdict. Keep traces tiny and synthetic.
- **A new check:** add a function decorated with `@rule("ID", what="...")` in `src/agentest/standards/rules.py`,
  reading only standard signals (OTel GenAI spans, A2A AgentCard, MCP tool annotations). Return `n/a` (via `need(...)`)
  when the evidence isn't in the trace, never a guessed `fail`. Add a pass and a fail case, cite sources in
  `src/agentest/refs.py`, then regenerate the docs (rule 6 above). See the [Author Guide](docs/AUTHOR-GUIDE.md).
- **A new test idea** without code: open a "New test idea" issue.

## Design rules

- **One runtime dependency: PyYAML.** Do not add runtime dependencies. Test-only tools go in the `dev` extra.
  Optional extras must stay optional and the core must run without them.
- **Agent-agnostic code.** Rules read standard artifacts only. No agent, tool, framework or vendor names in rule
  logic, and no per-agent special cases; `tests/test_agent_independence.py` enforces this.
- **Deterministic and offline.** No network calls and no model in the pass/fail path.
- Say **coverage**, not compliance. agentest does not certify anything.

## Sign your commits (DCO)

We use the [Developer Certificate of Origin](https://developercertificate.org/). Add a sign-off line to each commit:

```bash
git commit -s -m "Add fail case for T5-015"
# adds: Signed-off-by: Your Name <you@example.com>
```

By signing off you confirm you wrote the change, or have the right to submit it, under the Apache-2.0 licence.

## Code of Conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Issues and triage

- Use the issue forms: bug, feature, new test idea, detection improvement, false positive (wrong `fail`), false negative (missed defect). Wrong-verdict
  reports need the check ID, the verdict `detail`, the expected verdict and a redacted trace.
- Labels are defined in [`.github/labels.yml`](.github/labels.yml): `type:*`, `check: T1`..`check: T7` / `check: X`,
  `status:*`, `needs-trace`, `good first issue`, `help wanted`.
- Looking for a first contribution? Filter by `good first issue`.
- A fix for a false positive or negative must add a regression test with the (redacted) trace, and must not name any
  agent, tool or vendor in a rule (the agent-independence audit enforces this).
- Never paste secrets or personal data. Questions: see [SUPPORT.md](SUPPORT.md) and the [FAQ](docs/FAQ.md).

## Reporting a security issue

Email srinivas AT testAIng.com instead of opening a public issue.
