# CI verdict diff: what your pull request changes

**AiEnsured agentest, an Agentic AI Testing platform** checks what an agent actually did, not only what it said. When you open a pull request, two small workflows tell reviewers which verdicts your change moves on the public example agents.

1. `verdict-diff` (trigger: `pull_request`) runs [`make eval`](EVAL.md) for the base and for your head on the in-repo example agents and uploads one small JSON file. It has a read-only token and no secrets, so it is safe for pull requests from first-time contributors. A maintainer may need to approve the run the first time.
2. `verdict-diff-comment` (trigger: `workflow_run`) posts or updates **one** comment on your pull request with the table of changed verdicts (pass, fail or n/a, before and after, per example agent and check). It does not check out or run your code. It reads the JSON as untrusted data: size-limited, validated field by field, and only validated values are written into the comment. The pull request number comes from the GitHub API, not from the file.

If nothing changes, no comment is posted. If an earlier comment exists and your next push removes all changes, the comment is updated to say so.

## What a changed verdict means

A changed verdict is not automatically wrong. It is information for the review:

- Intended (you fixed a false alarm or a miss): say so in the pull request and regenerate the snapshot with `python scripts/verdict_snapshot.py --write` in the same pull request. A maintainer decides whether the new verdict is right.
- Not intended: your change reached further than you meant. Narrow it, then push again.

## Run the same thing locally

```bash
make eval BASE=origin/main
```

## Safety design

- No `pull_request_target`; the token of the run that executes pull-request code is read-only.
- The write-token workflow has no checkout and no shell step; it only parses and validates JSON and calls the comments API.
- Only a comment made by `github-actions[bot]` that starts with the hidden marker is updated.
- The comment contains verdict words and check IDs only. It contains no scores.

Related: [EVAL.md](EVAL.md), [CONTRIBUTING.md](../../CONTRIBUTING.md).
