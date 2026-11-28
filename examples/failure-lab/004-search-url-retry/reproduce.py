"""Judge the recorded original and fixed traces for Failure Lab 004.

    python examples/failure-lab/004-search-url-retry/reproduce.py --variant original
    python examples/failure-lab/004-search-url-retry/reproduce.py --variant fixed

The original trace is the recorded case 1 run of the bundled agent ``a22``.
The fixed trace is a recorded run of the same task with the repair described
in the README. Judging is offline: no API key, no model and no network.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import agentest
from agentest.cli import main as agentest_cli

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CARD = ROOT / "agents" / "a22" / "agent-card.json"
TOOLS = ROOT / "agents" / "a22" / "tools.json"
CHECKS = "T5-009"
VARIANTS = ("original", "fixed")


def judge(variant: str) -> int:
    otlp = HERE / "traces" / f"{variant}.otlp.jsonl"
    return agentest_cli([
        "std", "run", "--otlp", str(otlp), "--card", str(CARD), "--tools", str(TOOLS),
        "--ids", CHECKS, "--format", "md",
    ])


def print_verdicts(variant: str) -> None:
    otlp = HERE / "traces" / f"{variant}.otlp.jsonl"
    print(f"variant: {variant}")
    for check in agentest.run(otlp, card=CARD, tools=TOOLS, ids=CHECKS):
        print(check.id, check.status, check.detail)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=VARIANTS, default="original")
    a = ap.parse_args()
    print_verdicts(a.variant)
    print()
    return judge(a.variant)


if __name__ == "__main__":
    sys.exit(main())
