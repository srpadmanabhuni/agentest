# See what your change does: `make eval`

**AiEnsured agentest, an Agentic AI Testing platform** checks what an agent actually did, not only what it said. Before you open a pull request that touches a check, run one command and read the table. It shows which verdicts moved.

```bash
pip install -e ".[dev]"
make eval
```

`make eval` runs every check on the public example agents in this repository (`agents/` and `examples/*/agents/`) and prints:

1. a per-check summary: for each check ID, how many example agents pass, fail or are n/a;
2. every verdict that differs from `main` (the example agents and the code of `main` are re-run from git, so you compare like with like).

No setup is needed beyond a clone with a `main` branch (`git fetch origin main:main` if you only have `origin/main`; or use `BASE=origin/main make eval`).

## Options

```bash
python scripts/eval_verdicts.py                         # summary for this checkout
python scripts/eval_verdicts.py --base origin/main      # summary plus verdicts that differ from origin/main
python scripts/eval_verdicts.py --ids T2-001 X-002      # only some checks
python scripts/eval_verdicts.py --mode strict           # one mode (strict or examples)
python scripts/eval_verdicts.py --json eval.json        # machine-readable verdicts
make eval BASE=origin/main EVAL_ARGS="--ids T2-001"
```

A diff looks like this:

```
Verdicts that differ from main on the public example agents: 1
  strict   a01                          T5-004   fail -> pass
```

## What it reads, and what it does not

- Only the example agents that ship in the repository. Paths given with `--agents` must stay inside the repository root, otherwise the command refuses.
- It does not read any data outside the checkout, calls no network and no model, and computes no scores. It is a verdict summary, not a benchmark.
- The same data feeds the verdict snapshot (`python scripts/verdict_snapshot.py`, `fixtures/standards/v3-verdicts.json`). If your change moves verdicts on purpose, regenerate the snapshot in the same pull request and say in the description why the new verdict is right; a maintainer decides.

## In a pull request

A pull request gets one automatic comment with the verdicts it changes on the public example agents (see [CI verdict diff](CI-VERDICT-DIFF.md)). `make eval` shows the same thing on your machine before you push.

Related: [CONTRIBUTING.md](../../CONTRIBUTING.md), the [weakest checks board](https://github.com/srpadmanabhuni/agentest/issues/113).
