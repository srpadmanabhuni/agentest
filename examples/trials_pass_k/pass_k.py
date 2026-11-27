#!/usr/bin/env python3
"""Compute pass@1, pass@k and pass^k per task from saved ``agentest std run --format json`` output.

Reads the ``trials`` summary emitted by ``agentest std run --format json`` and prints the unbiased
binomial estimators outside the scorer so check verdicts are never altered:

    pass@k = 1 - C(n - c, k) / C(n, k)
    pass^k = C(c, k) / C(n, k)

Usage:
    agentest std run --agents examples/trials_pass_k --format json --out build/trials-verdicts.json
    python examples/trials_pass_k/pass_k.py build/trials-verdicts.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def pass_at_k(n: int, passes: int, k: int) -> float:
    """Unbiased estimator of the probability that at least one of ``k`` drawn trials succeeds."""
    if k < 1 or n < k or passes < 0 or passes > n:
        raise ValueError(f"pass@k needs 1 <= k <= n and 0 <= passes <= n, got n={n} passes={passes} k={k}")
    if n - passes < k:
        return 1.0
    return 1.0 - math.comb(n - passes, k) / math.comb(n, k)


def pass_all_k(n: int, passes: int, k: int) -> float:
    """Estimator of the probability that all ``k`` drawn trials succeed."""
    if k < 1 or n < k or passes < 0 or passes > n:
        raise ValueError(f"pass^k needs 1 <= k <= n and 0 <= passes <= n, got n={n} passes={passes} k={k}")
    if passes < k:
        return 0.0
    return math.comb(passes, k) / math.comb(n, k)


def load_trials(source: str | Path) -> list[dict]:
    """Load the ``trials`` array from a saved ``agentest std run --format json`` file or stdin (``-``)."""
    if str(source) == "-":
        raw = sys.stdin.read()
    else:
        path = Path(source)
        if not path.is_file():
            raise ValueError(f"{path} is not a file")
        raw = path.read_text(encoding="utf-8")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"input is not valid JSON: {exc.msg} (line {exc.lineno})") from None
    trials = doc.get("trials") if isinstance(doc, dict) else None
    if not isinstance(trials, list) or not trials:
        raise ValueError(
            "expected a 'trials' array from `agentest std run --format json` "
            "(ensure tasks have 2+ recorded runs and use `--format json`)"
        )
    return trials


def summarize_trials(trials: list[dict]) -> list[dict]:
    """Compute pass@1, pass@n and pass^n for each task row in ``trials``."""
    rows: list[dict] = []
    for entry in trials:
        n = int(entry["k"])
        passes = int(entry["passes"])
        rows.append({
            "agent": str(entry.get("agent", "")),
            "task": str(entry["task"]),
            "n": n,
            "passes": passes,
            "pass@1": pass_at_k(n, passes, 1),
            "pass@k": pass_at_k(n, passes, n),
            "pass^k": pass_all_k(n, passes, n),
        })
    return rows


def format_table(rows: list[dict]) -> str:
    """Format per-task trial counts, pass@1, pass@k and pass^k as an aligned text table."""
    ns = {r["n"] for r in rows}
    k_label = str(next(iter(ns))) if len(ns) == 1 else "k"
    h_pass_at_k = f"pass@{k_label}"
    h_pass_all_k = f"pass^{k_label}"

    task_w = max([len("task"), *(len(r["task"]) for r in rows)])
    count_strs = [f"{r['passes']}/{r['n']}" for r in rows]
    cnt_w = max([len("passes"), *(len(s) for s in count_strs)])

    header = f"{'task':<{task_w}}  {'passes':>{cnt_w}}  {'pass@1':>8}  {h_pass_at_k:>8}  {h_pass_all_k:>8}"
    sep = f"{'-' * task_w}  {'-' * cnt_w}  {'-' * 8}  {'-' * 8}  {'-' * 8}"
    lines = [header, sep]
    for r, c_str in zip(rows, count_strs, strict=True):
        lines.append(
            f"{r['task']:<{task_w}}  {c_str:>{cnt_w}}  "
            f"{r['pass@1']:8.4f}  {r['pass@k']:8.4f}  {r['pass^k']:8.4f}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Path to JSON written by `agentest std run --format json`, or '-' to read stdin",
    )
    args = parser.parse_args(argv)
    if args.input == "-" and sys.stdin.isatty():
        parser.print_usage(sys.stderr)
        print("pass a JSON file from `agentest std run --format json` or pipe stdin", file=sys.stderr)
        return 2
    try:
        trials = load_trials(args.input)
        rows = summarize_trials(trials)
    except (ValueError, KeyError, TypeError) as exc:
        print(f"pass_k.py: {exc}", file=sys.stderr)
        return 2
    print(format_table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
