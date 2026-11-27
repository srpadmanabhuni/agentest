# Contributing

Thanks for helping. Contact: Dr Srinivas Padmanabhuni, srinivas AT testAIng.com.

**New here?** Join [agentest contributor week, 23–30 Nov 2026](https://github.com/srpadmanabhuni/agentest/discussions/100): ten starter issues, public credit for every merged pull request, and a chance to co-own a check family. Enhance and contribute by opening a pull request against `main`.

**Where to ask questions:** join the [agentest Discord](https://discord.gg/7mnsWRGt5N) and use the #help and #contributors channels.

## Why your contribution matters

AiEnsured agentest, an Agentic AI Testing platform, is relevant for responsible and safe AI agents because it checks what the agent actually did, not only what it said ([each point, with its source](docs/START_HERE.md#what-makes-agentest-different)). A merged check runs in CI for teams testing tool-using agents. The 165 tests include designs from the open checklist dataset on Hugging Face (linked under [What it checks](README.md#what-it-checks)). A check that implements one of those designs makes that design executable, and the checks are part of the agentest paper. Every test case you add is a real bug that the next team does not have to find on its own.

## First install

```bash
pip install agentest-ai
```

Try agentest on your own agent, and share what it caught or missed as an issue or in [Discussions](https://github.com/srpadmanabhuni/agentest/discussions).

To open a pull request, clone the repository and install the dev extra:

```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Confirm that checkout with the [two-minute local path](#two-minute-local-path), then follow [your first pull request in about ten minutes](#your-first-pull-request-in-about-ten-minutes).

## Two-minute local path

Confirm a local checkout works, then come back for a first pull request. This is the clone path for a pull request. The published install is [First install](#first-install):

```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q tests/test_contribute_trace.py
```

That last command should pass in well under a minute once the install has finished. The full suite is `python -m pytest -q` and takes a few minutes. Prefer no local setup? Open the repo in a [GitHub Codespace](https://codespaces.new/srpadmanabhuni/agentest) (free tier is enough).

## Set up

To confirm the environment only, use the [two-minute local path](#two-minute-local-path) first.


```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q && ruff check src tests scripts && python scripts/check_catalog_pins.py
```

Prefer no local setup? Open the repo in a [GitHub Codespace](https://codespaces.new/srpadmanabhuni/agentest) (free tier is enough). The devcontainer in `.devcontainer/devcontainer.json` uses Python 3.12 and runs `pip install -e ".[dev]"`, so `pytest` and `agentest` work as soon as it opens.

Optional, same lint as CI before you push: `pip install pre-commit && pre-commit install`. The hooks are in `.pre-commit-config.yaml` and run `ruff check`. This is separate from the published agentest pre-commit hooks that judge traces (see `.pre-commit-hooks.yaml` and [docs/developers/GITHUB-ACTION.md](docs/developers/GITHUB-ACTION.md)).

## Response promise

- **First response within 24 hours** to every new issue and pull request.
- **Your first pull request is reviewed within 24 hours.** If this is your first contribution to agentest, say so in the description and we will review it within a day and help you get it merged.
- **Review within 48 hours** of a pull request that is ready.

If we miss any of these, comment on your pull request and we will pick it up.

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
8. Add a short Markdown file under [`changelog.d/`](changelog.d/README.md) (one file per pull request), with one bullet in the same style as the Unreleased list. Do not edit released sections of `CHANGELOG.md`.

## Run the tests

```bash
python -m pytest -q                       # full suite, offline, a few minutes
python -m pytest -q tests/test_framework.py         # one file
ruff check src tests scripts
```

CI runs the same commands on every pull request.

To see what your change does to the verdicts on the public example agents, run `make eval`
(see [docs/contributing/EVAL.md](docs/contributing/EVAL.md)). It prints a per-check summary and every verdict that differs from `main`. A pull request also gets one automatic comment with the same table ([CI verdict diff](docs/contributing/CI-VERDICT-DIFF.md)).

## Add a check or a test case

- **A test case for an existing check** (a good first pull request): add a small passing and a small failing
  example (a redacted OTLP trace, plus the AgentCard / MCP tools list if the check needs them) under
  `tests/fixtures/`, and a test in `tests/` that asserts the verdict. Keep traces tiny and hand-written.
- **A new check:** add a function decorated with `@rule("ID", what="...")` in `src/agentest/standards/rules.py`,
  reading only standard signals (OTel GenAI spans, A2A AgentCard, MCP tool annotations). Return `n/a` (via `need(...)`)
  when the evidence isn't in the trace, never a guessed `fail`. Add a pass and a fail case, cite sources in
  `src/agentest/refs.py`, add the check's row to [`taxonomy/asi-mapping.yaml`](taxonomy/asi-mapping.yaml)
  (`python scripts/gen_taxonomy_docs.py --missing` prints a stub; use `no ASI mapping` and a reason when no OWASP Agentic
  Top 10 entry fits), then regenerate the docs (rule 6 above and `python scripts/gen_taxonomy_docs.py`).
  See the [Author Guide](docs/AUTHOR-GUIDE.md).
- **A New test** (`NT-044` and later): follow [Add a New test](#add-a-new-test).
- **A new test idea** without code: open a [New test idea](.github/ISSUE_TEMPLATE/new-test-idea.yml) issue.

## Add a New test

New tests use distinct IDs: `NT-001`, `NT-002`, and so on. Never use a T-numbered ID. `NT-001` through `NT-043` are already used. Do not reuse them. The next free ID is `NT-044`.

They stay opt-in and are not added to the published count, which stays at 165 tests. Do not write a new total.

A New test must be deterministic and agent-agnostic. It must return `n/a` when the needed signal is absent, never a guessed `fail`. Read standard signals only (OTel GenAI spans, A2A AgentCard, MCP tool annotations). No agent, tool, framework or vendor name in the check.

How New tests run is in [docs/new-tests/README.md](docs/new-tests/README.md). An idea without code goes on the [New test idea](.github/ISSUE_TEMPLATE/new-test-idea.yml) issue template. The steps below are enough to open the pull request.

Copy the layout of [b5.py](src/agentest/standards/new_tests/b5.py). That batch already holds `NT-041`, `NT-042` and `NT-043` ([b5.md](docs/new-tests/b5.md)), so the next check is a new batch, `b6`, for `NT-044`. Modules are found by name, the same way `b5.py` is found.

1. **Module.** Add `src/agentest/standards/new_tests/b6.py`. Copy the imports and the `@rule` shape from [b5.py](src/agentest/standards/new_tests/b5.py):

   ```python
   from agentest.standards.expr import R, ok
   from agentest.standards.rules import Ctx, need, rule

   # Ref NT-044: internal design (catalog/new-tests/b6.jsonl NT-044)
   @rule("NT-044", what="One sentence: what a passing trace shows.")
   def _nt_044(c: Ctx, tid: str) -> R:
       need(signal_present, "the needed signal is absent")
       return ok(passed, "what the trace showed")
   ```

   `need(...)` returns `n/a`. The names `signal_present` and `passed` stand in for the check. When the needed signal is absent, stop at `need` and return `n/a`, never a guessed `fail`.

2. **Catalogue fragment.** Add `catalog/new-tests/b6.jsonl`, one JSON object on one line. Copy a row from [catalog/new-tests/b5.jsonl](catalog/new-tests/b5.jsonl) and set `id` to `NT-044`, `class_id` to `NT`, and `batch` to `b6`. Keep the same fields: `title`, `article_test`, `article_title`, `objective`, `acceptance_criteria` (pass, fail, and n/a), `trace_attributes`, `severity`, and `eval_group`.

3. **Docs.** Add `docs/new-tests/b6.md` in the shape of [docs/new-tests/b5.md](docs/new-tests/b5.md): the ID, the attributes it reads, and the pass, fail, and n/a rules. Link that page from [docs/new-tests/README.md](docs/new-tests/README.md) the way the README links [b5.md](docs/new-tests/b5.md). Leave the published pages under `docs/tests/` as they are. This check is not part of that list.

4. **Tests.** Add `tests/test_new_tests_b6.py` in the shape of [tests/test_new_tests_b5.py](tests/test_new_tests_b5.py). Build three example traces and assert pass, fail, and n/a. Use example ids (`R-1`, `example.invalid`). The n/a trace leaves out the needed signal.

5. **Taxonomy row.** Add the check to [`taxonomy/asi-mapping.yaml`](taxonomy/asi-mapping.yaml): `python scripts/gen_taxonomy_docs.py --missing` prints a stub. Pick a failure category, map it to an [OWASP Agentic Top 10](docs/taxonomy/ASI-MAPPING.md) entry only where it fits (`direct` or `partial`), otherwise leave `no ASI mapping` with a reason. Then run `python scripts/gen_taxonomy_docs.py`. A test fails if a registered check has no row.

6. **Changelog.** Add a short file under [`changelog.d/`](changelog.d/README.md) (one file per pull request). Say the check is opt-in and that the published count stays 165. Do not write a new total, and do not edit released sections of `CHANGELOG.md`.

Run `python -m pytest -q tests/test_new_tests_b6.py`, then `python -m pytest -q`. Sign the commit (`git commit -s`) and open the pull request against `main`.

Another check in the same batch uses the next free ID (`NT-045`, then `NT-046`). A later batch copies this layout again (`b7`, and so on).

## Bring an agent trace, contribute a test

The pattern is two tiny example traces and one existing check: `tests/fixtures/contribute/`
(`order_ok` passes `T2-001`, `order_bad` fails it) and `tests/test_contribute_trace.py`.
Copy that shape. Do not start by editing a rule.
The executable path is [walkthrough 1](docs/walkthroughs/01-verify-before-acting.md#sanitized-trace-then-the-fixed-trace):
run `T2-001` on `order_bad`, read the detail, then run the same check on `order_ok`.

Walkthroughs of the refill demo are in [docs/walkthroughs/](docs/walkthroughs/README.md).
A native log converted with `agentest std import` is [walkthrough 5](docs/walkthroughs/05-bring-your-own-log.md).

What not to include:

- No private or customer data, names of real people, account numbers, or message contents from a real system.
- No credentials, API keys, tokens, cookies, or private URLs.
- No blind-round material: nothing from `docs/blind`, and no unpublished seed traces.
- Use example ids (`R-1`, `example.invalid`). If you must show a real trace, redact it first and say that you did.

A maintainer replies within 24 hours and reviews within 48 hours ([Response promise](#response-promise)).
Small diffs are easier to review. A draft is fine. You may be asked to redact, to drop unrelated files,
or to add the missing pass or fail case. Comments are about the change. Follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Submit a reproducible agent failure

Found an agent doing something it should not, and can show it from a recorded run? That becomes an entry in the [failure registry](registry/README.md): a stable ID (`AFR-NNNN`), a category from the [failure taxonomy](docs/taxonomy/TAXONOMY.md), the [OWASP Agentic Top 10](docs/taxonomy/ASI-MAPPING.md) entries the failing checks map to, your trace, and the verdicts agentest must give. You are credited in the entry and in [CONTRIBUTORS.md](CONTRIBUTORS.md).

**Easiest path (no code):** open a [reproducible agent failure](.github/ISSUE_TEMPLATE/reproducible-failure.yml) issue. Say what the run shows, which checks fail (or that none do: that is a new check idea), and how to reproduce it. A maintainer turns it into an entry with you.

**Pull request path:**

1. Record the run as an OTLP trace and add it under a [Failure Lab](examples/failure-lab/README.md) case, or `tests/fixtures/` for a very small one. A failing run plus, if you can, a fixed run that passes. Hand-written or scripted agents are fine; say so.
2. Run the checks (`agentest std run --otlp your.otlp.jsonl --ids ...`) and note which fail on the failing run and which pass on the fixed one.
3. Copy [`registry/entries/AFR-0002.json`](registry/entries/AFR-0002.json) to the next free ID. Set the category and ASI IDs from the mapping of your failing checks, the paths to your trace, and the expected verdict for each check.
4. Run `python scripts/run_registry.py` (it validates the entry and re-runs it) and `python scripts/run_registry.py --write-index`.
5. Add a short `changelog.d/` file, sign off the commit (`git commit -s`), and open the pull request. CI re-runs every entry.

What an entry must not contain: secrets, keys, tokens, personal data, customer data or names of real people (use `R-1` and `example.invalid`). It must also not turn a finding about one example into a verdict on a framework, model or product: scope it to the example and version, and write what it does not show.

A Failure Lab case adds its registry entry in the same pull request, and a test fails if one is missing. Links to a public incident catalogue are welcome where a record describes the same kind of failure, and never required.

## Your first pull request in about ten minutes

Add one tiny example trace for an existing check. Do not edit rule code on your first pull request.

```bash
git clone https://github.com/srpadmanabhuni/agentest.git && cd agentest
python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
ls tests/fixtures/contribute/          # order_ok passes T2-001, order_bad fails it
python -m pytest -q tests/test_contribute_trace.py
```

1. Copy `tests/fixtures/contribute/order_bad` to `tests/fixtures/contribute/<your_case>` and change the trace (example ids only).
2. Add a test in `tests/test_contribute_trace.py` that asserts the verdict you expect for one check ID.
3. Run `python -m pytest -q tests/test_contribute_trace.py`, then the full `python -m pytest -q`.
4. Add a short file under [`changelog.d/`](changelog.d/README.md) and commit with a sign-off: `git commit -s`.
5. Open a pull request against `main` that names the check ID.

Prefer to try agentest outside this repo first? [agentest-starter](https://github.com/srpadmanabhuni/agentest-starter) is a
template repo with an example agent, a run script and a CI workflow. A New test (`NT-044` onward) follows [Add a New test](#add-a-new-test). Stuck? Ask in
[Discussions](https://github.com/srpadmanabhuni/agentest/discussions) or pick a `good first issue`.

## Label traces (no code needed)

Independent labels are how we learn how well a check works. [Label 10 traces in about 30 minutes](docs/contributing/LABELLING.md):
`python scripts/labelling.py batch --labeller YOUR_GITHUB_HANDLE`. Two people label each trace without seeing each other's labels,
a maintainer settles disagreements, and the labels are locked with a hash before any prediction runs.

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

## Picking a good first issue

A maintainer applies the [`good first issue`](https://github.com/srpadmanabhuni/agentest/labels/good%20first%20issue) label. It means the task is small, the result is described in the issue, and you can finish it without already knowing the whole catalogue. The label is not an assignment, and commenting does not reserve the issue.

For a still smaller, step-by-step first change (one file, about 15–30 minutes), pick a [`first-timers-only`](https://github.com/srpadmanabhuni/agentest/labels/first-timers-only) issue.

1. Open [open issues with that label](https://github.com/srpadmanabhuni/agentest/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
2. Read the issue through before you write code. Prefer one that names the file or the check ID, says what done looks like, and can be shown with a tiny example trace.
3. Skip an issue that says the code is not on `main` yet, that needs a private trace you do not have (`needs-trace`), or that already has someone working on it. If two issues edit the same rule, pick one.
4. Match the issue to the kind of change you want to make:
   - A docs issue, such as a correction to a crosswalk, is prose and sources.
   - A detection issue is one existing rule plus a passing test and a failing test. Start from the file and the acceptance list in the issue.
   - An adapter or example issue is a small offline recording. No new runtime dependency, and no network call in CI.
   - A CLI issue is a filter or flag with a unit test. Stay inside the command the issue names.
5. Comment on the issue that you are starting, so two people do not write the same patch. Then open a pull request against `main`. A maintainer may still ask you to change the approach.
6. Follow the rules in this file: one check when you can, example data only, a sign-off, and a short file under [`changelog.d/`](changelog.d/README.md).

We reply within 24 hours and review within 48 hours ([Response promise](#response-promise)). A short diff is easier to review.

Questions about a good first issue? Join the [agentest Discord](https://discord.gg/7mnsWRGt5N) and use the #help and #contributors channels.

## Help own a check family

We invite co-maintainers for one area each. If a family matters to you, you can help keep it healthy:

- **Extension families:** red teaming, privacy, bias, explainability, data lineage and multi-agent (the opt-in packs in progress, see [pull request #99](https://github.com/srpadmanabhuni/agentest/pull/99)).
- **Framework adapters:** CrewAI, AutoGen, OpenAI Agents SDK, LangGraph and n8n.

What a family owner does:

- Triages issues and answers questions for that family.
- Reviews pull requests in that area, with a maintainer.
- Keeps the family's docs and sample traces current.
- Is named as the family's co-maintainer in the README.

**Three merged pull requests make you a co-maintainer candidate.** After your third merged pull request (small ones count), say which family you would like to look after and a maintainer invites you. The roles and what stays with the maintainer are in [GOVERNANCE.md](GOVERNANCE.md).

**How to volunteer:** comment on the [contributor week Discussion](https://github.com/srpadmanabhuni/agentest/discussions/100) with the family you want and one line about your background.

Framework adapters that are wanted, with an issue for each: [Adapters wanted](docs/integrations/ADAPTERS-WANTED.md).

## Contributor office hours

Two 45-minute contributor office hours during contributor week (planned: **Tuesday 24 Nov** and **Thursday 26 Nov 2026**, 19:30 IST / 14:00 UTC). Bring a pull request, a half-written check, a labelling batch or a question about an adapter. Office hours are **async first**: post your question in the [contributor week thread](https://github.com/srpadmanabhuni/agentest/discussions/100) before the session and a maintainer answers there, so you get an answer even if you cannot attend. The live link will be posted in that thread before each session.

## Contributor week

[agentest contributor week runs 23–30 Nov 2026](https://github.com/srpadmanabhuni/agentest/discussions/100). It lists 10 starter issues and explains the recognition: a daily leaderboard of merged pull requests, a shout-out post for every merged contributor, and a LinkedIn recommendation from Dr. Srinivas Padmanabhuni for the top 3 contributors if they want one. There is no money and there are no prizes.

## Issues and triage

- Use the issue forms: bug, feature, documentation, new test idea, detection improvement, false positive (wrong `fail`), false negative (missed defect). Wrong-verdict
  reports need the check ID, the verdict `detail`, the expected verdict and a redacted trace.
- Labels are defined in [`.github/labels.yml`](.github/labels.yml): `type:*`, `check: T1`..`check: T7` / `check: X`,
  `status:*`, `needs-trace`, `good first issue`, `first-timers-only`, `help wanted`.
- Looking for a first contribution? Use [Picking a good first issue](#picking-a-good-first-issue).
- A fix for a false positive or negative must add a regression test with the (redacted) trace, and must not name any
  agent, tool or vendor in a rule (the agent-independence audit enforces this).
- Never paste secrets, customer data, credentials, or blind-round material. Questions: see [SUPPORT.md](SUPPORT.md) and the [FAQ](docs/FAQ.md).

## Crediting contributors

After a pull request is merged, a maintainer credits the author in two places:

1. Comment on the pull request (or any issue):

   `@all-contributors please add @username for doc`

   Use the type that matches the work: `code`, `doc`, `test`, `data`, or `translation`. The [all-contributors bot](https://allcontributors.org/docs/en/bot/usage) updates `.all-contributorsrc` and the README contributors table. The [All Contributors GitHub App](https://github.com/apps/allcontributors) must be installed on this repository for that comment to work.

2. Add a line to [CONTRIBUTORS.md](CONTRIBUTORS.md) with the author's GitHub profile, the merged pull request, and a short description. That file is the record of which pull request was merged.

Do not add someone until their pull request is merged. If a credit is missing, the author can comment on their pull request.

## Reporting a security issue

Do not open a public issue. Follow [SECURITY.md](SECURITY.md): email srinivas AT testAIng.com, or use GitHub private vulnerability reporting.
