## What this changes

<!-- One or two sentences. Link the issue: "Fixes #123". -->

## Type

- [ ] Detection fix (false alarm or miss)
- [ ] New check / test case
- [ ] Adapter / importer
- [ ] Docs
- [ ] Other

## Checklist

- [ ] `python -m pytest -q` and `ruff check src tests scripts` pass locally
- [ ] A rule change adds a passing **and** a failing test case (small, synthetic, redacted)
- [ ] No new runtime dependency (PyYAML only)
- [ ] Rule code is agent-agnostic: no agent, tool, framework or vendor names
- [ ] Generated docs regenerated if rules changed (see CONTRIBUTING, rule 6)
- [ ] `CHANGELOG.md` has a line under `## [Unreleased]`
- [ ] Commits are signed off (`git commit -s`)
