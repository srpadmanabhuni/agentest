# Releasing agentest

We aim for small, frequent releases: a patch or minor release about once a week, whenever `main` has user-visible changes. Each release ships to PyPI as `agentest-ai`.

## Weekly cadence

1. **Monday to Thursday:** merge pull requests. Each one adds a short file under `changelog.d/` (see [changelog.d/README.md](changelog.d/README.md)).
2. **Friday:** if `Unreleased` has user-visible changes, cut a release. If it does not, skip that week.
3. Keep releases small. A release with one useful change beats a large release that waits for weeks.

## Steps

1. Bump the version in `RELEASE`, then rewrite the version stamps across the repo:

   ```bash
   python scripts/check_versions.py --bump
   ```

2. Add the coverage rows for the new version to `docs/HOW-IT-WORKS.md` (`python scripts/check_versions.py` tells you if they are missing). Then regenerate `llms-full.txt`:

   ```bash
   python scripts/gen_llms_full.py
   ```

3. Run `python scripts/collect_changelog.py --delete` to prepend `changelog.d/` fragments under `## Unreleased`. Then, in `CHANGELOG.md`, rename `## Unreleased` to `## [X.Y.Z] - YYYY-MM-DD` and add a fresh heading and the `changelog.d/` note above it (keep the wording already in that file).
4. Run `pytest -q` and open a pull request. Merge it once CI is green. If the Hugging Face checklist dataset revision or row counts changed intentionally, update `scripts/hf_dataset_counts.json` (checked by `python scripts/check_hf_dataset_counts.py` and `.github/workflows/hf-dataset-counts.yml`) in the same change.
5. Tag the merge commit and publish a GitHub Release:

   ```bash
   gh release create vX.Y.Z --target main --title "vX.Y.Z: <one-line headline>" --notes-file notes.md
   ```

   Publishing the release runs `.github/workflows/publish.yml`, which uploads to PyPI through trusted publishing. No token is stored.
6. Check the release from a clean virtual environment:

   ```bash
   python3 -m venv /tmp/v && . /tmp/v/bin/activate
   pip install agentest-ai==X.Y.Z
   agentest --version
   agentest demo
   ```

## Release notes

- Start with a one-line headline that says what a user can do now that they could not do before.
- Show the change: a short GIF, terminal output or one command.
- Keep the PyPI install near the top, in its own code block.
- State plainly whether any rule, scorer or verdict changed.
- Use [docs/RELEASE_NOTES_TEMPLATE.md](docs/RELEASE_NOTES_TEMPLATE.md) as the starting point.
