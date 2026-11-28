# AGENTS.md

Notes for coding agents working in this repository.

The public path from install to a first verdict is [Start here](docs/START_HERE.md#the-path): install, run the demo, then judge your own trace. [Use from Python](docs/START_HERE.md#use-from-python) is the next step on that path. Document it there. Do not add a second install sequence or a second copy of that section.

The PyPI package name is agentest-ai and the import and the command stay `agentest`.

## Install for this checkout

From the repository root:

```bash
python -m venv .venv
```

```bash
. .venv/bin/activate
```

```bash
pip install -e ".[dev]"
```

Python 3.11 or newer. The runtime dependency is PyYAML. The `dev` extra adds pytest, ruff and jsonschema.

## Tests and checks

```bash
python -m pytest -q
```

```bash
ruff check .
```

CI is [`.github/workflows/ci.yml`](.github/workflows/ci.yml). It runs ruff, pytest, the catalogue pin check, the coverage-table check, the framework generators in `--check` mode, and `agentest std` validate and run.

Doc checks live in the test suite:

- Relative links in Markdown: `tests/test_doc_links.py`
- Runnable bash blocks in the user guide, the author guide and getting started: `tests/test_doc_commands.py`
- The README demo block and the README quickstart row: `tests/cli/test_demo.py` and `tests/test_readme_quickstart.py`
- `llms-full.txt` matches `PYTHONPATH=src python scripts/gen_llms_full.py`

`make test` and `make lint` call the same pytest and ruff commands.

## Where the checks and the docs live

| What | Where |
|---|---|
| Check implementations | `src/agentest/standards/rules.py` |
| Catalogue rows the runner loads | `catalog/` |
| Per-ID pages | `docs/tests/` |
| Docs index | `docs/README.md` |
| Start here path | `docs/START_HERE.md` |
| Recipes | `docs/recipes/` |
| Tutorials | `docs/tutorials/` |
| Tutorial notebooks | `notebooks/tutorials/` |
| CLI entry | `src/agentest/cli.py` |

When a public page states a test count, state 165 tests. Do not publish a breakdown of that count.

The published total is `PUBLISHED_TEST_COUNT` in `src/agentest/standards/catalog.py`. `published_ids()` is the registry. A CI test (`tests/test_published_count.py`) fails if that total, or the README, `agentest --help`, or `agentest list` output, disagrees with 165.

Internal definition (do not copy this composition onto a public page, the CLI, a pull request, or an issue):

- the 110 catalogue IDs (`CATALOGUE_IDS`)
- the 20 repo extensions (`X_IDS`)
- New tests through NT-030
- the five responsible-AI additions (`RAI_ADDITION_IDS`)

Later New tests (after NT-030) and extension packs are opt-in and are not part of the 165. The default `std run` still judges `ALL_IDS` only; the remaining published IDs are selected with `--ids`, `list --opt-in`, or `--new-tests`.
