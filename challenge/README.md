# The agentic evals challenge

Twenty example agent traces, every one of them broken in some way. Your job is to find out what each agent actually did wrong. It runs offline, with no API key, no sign-up and no model. Each trace is a recorded run of an agent that ships with agentest, either a reference agent or one of the sample agent profiles.

**Contributor week runs from 23 to 30 November 2026.** Entries are welcome after that too. The [leaderboard](LEADERBOARD.md) lists every solver.

## 1. Install

```bash
pip install agentest-ai
```

The traces ship inside the package, so you do not need a clone.

## 2. Warm up

```bash
agentest demo
```

The demo prints a pass/fail/n/a summary for one bundled sample agent, with a few example findings.

## 3. The 20 traces

Run each command, read the failing checks, and work out the root cause: what the agent did, in plain words, and which step should have been different. Every check ID has a page with its pass and fail criteria in [docs/tests](../docs/tests/README.md). Add `--html report.html` to any command if you want a report you can click through.

| # | Agent | What it is | Command |
|---|---|---|---|
| 1 | `a71` | Order fulfilment saga: reserve stock, book a carrier, print a label, and undo the earlier steps if one fails | `agentest std run --agent a71 --format md` |
| 2 | `a73` | Web research fetcher with a published host allow-list | `agentest std run --agent a73 --format md` |
| 3 | `a74` | File workspace agent: write, checksum, archive, soft and hard delete | `agentest std run --agent a74 --format md` |
| 4 | `a75` | CRM bulk updater: search, bulk update, accounts and contacts | `agentest std run --agent a75 --format md` |
| 5 | `a76` | Multi-turn office concierge with memory, to-dos and an audit trail | `agentest std run --agent a76 --format md` |
| 6 | `a78` | IAM access desk: L1 triage hands access requests to L2, with approvals and break-glass | `agentest std run --agent a78 --format md` |
| 7 | `a80` | Cross-border payout saga: KYC, a fresh FX rate, beneficiary, payout, and reversal on failure | `agentest std run --agent a80 --format md` |
| 8 | `a82` | File workspace agent, revised version of a74 | `agentest std run --agent a82 --format md` |
| 9 | `a84` | Multi-tenant analytics export, revised version with server-side tenant and recipient fences | `agentest std run --agent a84 --format md` |
| 10 | `a90` | File workspace agent, variant of a74 with planted defects | `agentest std run --agent a90 --format md` |
| 11 | `a91` | CRM bulk updater, variant of a75 with planted defects | `agentest std run --agent a91 --format md` |
| 12 | `a92` | Workplace concierge, variant of a76 with planted memory defects | `agentest std run --agent a92 --format md` |
| 13 | `a93` | IAM access desk, variant of a78 with planted approval defects | `agentest std run --agent a93 --format md` |
| 14 | `a94` | Web research fetcher, variant of a73 with planted injection defects | `agentest std run --agent a94 --format md` |
| 15 | `a95` | Pull-request review bot with planted defects | `agentest std run --agent a95 --format md` |
| 16 | `a96` | Cross-border payout saga, variant of a80 with planted defects | `agentest std run --agent a96 --format md` |
| 17 | `a97` | Inventory adjuster with planted defects | `agentest std run --agent a97 --format md` |
| 18 | `leaky` | Sample agent profile `leaky` | `agentest std run --agent leaky --format md` |
| 19 | `flaky_plan` | Sample agent profile `flaky_plan` | `agentest std run --agent flaky_plan --format md` |
| 20 | `hallucinator` | Sample agent profile `hallucinator` | `agentest std run --agent hallucinator --format md` |

Several traces fail more than one check, and sometimes one root cause sets off several checks at once. A good answer names the root cause, not just the list of IDs.

## 4. Submit

1. Create `challenge/solutions/<your-github-handle>.md`. For each trace you solved, write a heading with the agent ID, then the root cause in one to three sentences, then the check IDs it explains and the step that should have been different.
2. In the same pull request, add your row to [LEADERBOARD.md](LEADERBOARD.md).
3. Open the pull request with the title `challenge: <your-github-handle>`.

You can solve any number of traces, and you can update your file later.

## Scoring

- **1 point** for each trace whose root cause a maintainer confirms.
- **3 points** for each verdict you show is wrong, whether a false positive or a false negative, in one of these 20 traces or anywhere else in agentest. Open a [false-positive or false-negative issue](https://github.com/srpadmanabhuni/agentest/issues/new/choose) with the trace and the reasoning, then link it from your solutions file.
- Ties are ordered by the date the pull request opened.

A maintainer reviews a first pull request within 24 hours. There are no prizes. You get your name on the leaderboard and in [CONTRIBUTORS.md](../CONTRIBUTORS.md).

## Rules

- Do not change rules, scorers or verdicts in a challenge pull request. If a verdict looks wrong, open an issue for it, which is worth more points anyway.
- Solutions are public. You may read other people's files, but credit them if you build on their answer.
- Follow the [code of conduct](../CODE_OF_CONDUCT.md).

## Next steps

- Run agentest on your own agent: `agentest std run --otlp your-trace.jsonl --format md`. See [Getting started](../docs/GETTING-STARTED.md).
- [Wall of caught failures](../docs/WALL-OF-CAUGHT-FAILURES.md): real failures from recorded runs, each with a one-command repro.
- Want to write code? See the issues labelled [contributor-week](https://github.com/srpadmanabhuni/agentest/labels/contributor-week).
