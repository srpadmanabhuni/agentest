# Governance

**AiEnsured agentest, an Agentic AI Testing platform** is maintained by Dr Srinivas Padmanabhuni. This page says how decisions are made and how a contributor becomes a co-maintainer. It is short on purpose.

## Roles

| Role | How you get it | What you can do |
|---|---|---|
| Contributor | open an issue, a discussion comment, a label file or a pull request | propose changes; everything goes through a pull request |
| Co-maintainer | **three merged pull requests** (any mix of code, tests, docs, adapters or [labelling](docs/contributing/LABELLING.md) batches), then an invitation | triage issues and answer questions for one family; review pull requests in that area with a maintainer; keep the family's docs and sample traces current; be named in the README for that family. Repository permissions beyond triage are granted case by case by the maintainer |
| Maintainer | the repository owner | merges, releases, final say |

There is no obligation attached to being a co-maintainer, and no money. You can step down at any time by saying so in the contributor discussion.

## The path to co-maintainer

1. Get three pull requests merged. Small ones count: a fixture pair, a docs fix, a good first issue.
2. Say which family you would like to look after (a check family, a framework adapter family, docs, or labelling) in the [co-maintainer discussion](https://github.com/srpadmanabhuni/agentest/discussions/102) or the [contributor week thread](https://github.com/srpadmanabhuni/agentest/discussions/100).
3. A maintainer replies with an invitation, or with what to do next. The README then names you for that family.

## What stays with the maintainer

- Changes to how checks score or what a verdict means. A pull request may propose them; a maintainer decides. A pull request that moves verdicts on the bundled example agents must say so (the CI verdict-diff comment shows it).
- Releases and what goes to package registries.
- Who may merge.
- Labels used for any published measurement: labels are locked before predictions run ([labelling](docs/contributing/LABELLING.md)).

## Everyone

Follow the [Code of Conduct](CODE_OF_CONDUCT.md). Sign off your commits ([DCO](CONTRIBUTING.md#sign-your-commits-dco)). Disagree in the open, about the change, not the person.
