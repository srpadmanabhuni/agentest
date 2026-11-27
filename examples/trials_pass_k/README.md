# Repeated trials: `pass@k` and `pass^k`

When an agent runs the same task more than once, a single pass or fail does not tell you
how reliably it behaves. This example bundles **3 tasks × 3 recorded trials** (9 traces total)
for one sample agent (`trial_bot`):

| Task | Trials passed | Pattern |
|---|---:|---|
| `task_reliable` | 3 / 3 | passes every trial |
| `task_flaky` | 2 / 3 | passes 2, fails 1 |
| `task_failing` | 0 / 3 | fails every trial |

`pass_k.py` reads the versioned JSON output from `agentest std run --format json` and
computes `pass@1`, `pass@3` and `pass^3` **outside the scorer**, so individual check verdicts
are never changed.

## Run from the repository root

Follow [Getting started](../../docs/GETTING-STARTED.md#1-install) to install, then run:

```bash
mkdir -p build
agentest std run --agents examples/trials_pass_k --format json --out build/trials-verdicts.json
python examples/trials_pass_k/pass_k.py build/trials-verdicts.json
```

You can also pipe the JSON report directly:

```bash
agentest std run --agents examples/trials_pass_k --format json | python examples/trials_pass_k/pass_k.py -
```

Expected output:

```text
task           passes    pass@1    pass@3    pass^3
-------------  ------  --------  --------  --------
task_reliable     3/3    1.0000    1.0000    1.0000
task_flaky        2/3    0.6667    1.0000    0.0000
task_failing      0/3    0.0000    0.0000    0.0000
```

## What the two metrics mean

For $n$ recorded trials of a task where $c$ trials pass, and a draw size $k$ ($1 \le k \le n$):

- **`pass@k`** $= 1 - \dfrac{\binom{n - c}{k}}{\binom{n}{k}}$: probability that **at least one** of
  $k$ drawn trials succeeds. Here `pass@1` is the single-attempt success rate ($c / n$), and
  `pass@3` checks whether the agent succeeded at least once across the 3 trials.
- **`pass^k`** $= \dfrac{\binom{c}{k}}{\binom{n}{k}}$: probability that **every one** of $k$
  drawn trials succeeds. With $k = n = 3$, `pass^3` is `1.0000` only when all 3 trials pass.

## When to use `pass@k` vs `pass^k`

Look at `task_flaky` (`2/3` passing): it scores **`pass@3 = 1.0000`** but **`pass^3 = 0.0000`**.

- **Use `pass@k` for reliability across retries:** choose it when a caller or harness can retry,
  run multiple candidates, and pick or verify a working solution (for example, offline batch
  exploration or retryable read-only lookups). A high `pass@k` means the agent *can* solve the
  task if given $k$ tries.
- **Use `pass^k` when every trial must succeed:** choose it for production workflows where the
  agent gets one shot per user request and occasional failures cannot be retried away (for
  example, billing updates, permission changes, or customer-facing actions). A low `pass^k`
  shows that single-attempt success (`2/3`) hides inconsistency that will hurt users.
