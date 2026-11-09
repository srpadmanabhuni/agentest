# Release notes template

GitHub builds the pull-request list from [`.github/release.yml`](../.github/release.yml) when a maintainer drafts a release. Copy this outline into that draft and edit it. This file does not publish a release, tag, or package.

Label each pull request with one of the labels in [`.github/labels.yml`](../.github/labels.yml) (or `bug`, `enhancement`, `documentation`) so it lands in the matching category. A pull request is listed under the first matching category. `ignore-for-release` leaves it out.

## agentest vX.Y.Z — short title

One or two sentences on what a user of the `agentest` command can do after this release. This is not certification. Do not add a measured score for how often a check is right or wrong.

Install from a clone or from git. The distribution name `agentest-ai` is not a live PyPI package until a maintainer says it is. Do not tell readers to run `pip install agentest-ai` while that is still true.

## Breaking changes

- None. Or: the command, the verdict, or the on-disk layout that changed, and what to do instead.

## Bug fixes

- Check ID or command, what was wrong, what the new behaviour is. Link the pull request.

## Detection

- Check ID, the behaviour that was mis-read, and the new passing case and failing case. No model judge.

## Features

- New check, flag, or output. Say which standard artifacts it reads (OpenTelemetry GenAI traces, A2A AgentCard, MCP tool annotations).

## Adapters and importers

- Framework or log dialect, and that the example stays offline.

## Documentation

- Page or walkthrough that changed, in a few words.

## Other changes

- Anything that did not match a category above.

## Catalogue

Name the catalogue revision this release vendors, and point at the dataset link already in the [README](../README.md). Do not invent a second dataset URL here.

## Checks before you publish

- [ ] Version matches `RELEASE`, `pyproject.toml`, and the [changelog](../CHANGELOG.md)
- [ ] `python scripts/check_versions.py` passes
- [ ] Notes do not claim certification, and do not add a measured score for how often a check is right or wrong
- [ ] Install instructions match what is actually published
