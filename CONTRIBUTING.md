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

## Reporting a security issue

Email srinivas AT testAIng.com instead of opening a public issue.
