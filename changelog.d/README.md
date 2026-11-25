# changelog.d

**AiEnsured agentest, an Agentic AI Testing platform** keeps released changelog sections stable. New user-visible changes are added here, one short Markdown file per pull request, so two open pull requests do not need to edit the same `## Unreleased` list in `CHANGELOG.md`.

## How to add a fragment

1. Create a file named after the issue or a short slug, for example `changelog.d/322.md`.
2. Put one bullet in it, in the same style as the existing Unreleased list (start the line with `- **Area:**`, and mention when the published count of 165 tests is unchanged).
3. Do not edit released sections of `CHANGELOG.md`. You do not need to add your bullet to that file as well.
4. Sign off the commit (`git commit -s`).

At release time a maintainer runs `python scripts/collect_changelog.py`, which prepends these fragments under `## Unreleased`, then follows [RELEASING.md](../RELEASING.md).
