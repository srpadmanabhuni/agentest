"""Run the bundled refill agent on one probe, record it, and judge it with agentest.

    python examples/failure-lab/002-note-injection/reproduce.py --variant original
    python examples/failure-lab/002-note-injection/reproduce.py --variant fixed

``original`` is the bundled agent with its note-following defect switched on, ``fixed`` is the bundled
reference variant. Writes traces/<variant>.native.jsonl (the agent's own log) and traces/<variant>.otlp.jsonl
(the same run as an OpenTelemetry GenAI trace). The agent is plain Python with a rule-based planner: no model,
no API key, no network, no framework.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMO = HERE.parents[1] / "agnostic_demo"
sys.path.insert(0, str(DEMO))

from refill_agent import PROBES, RefillAgent  # noqa: E402

import agentest  # noqa: E402
from agentest.cli import main as agentest_cli  # noqa: E402

AGENT = DEMO / "agents" / "refill_bot"
MAP = DEMO / "import" / "map.json"
CARD = AGENT / "agent-card.json"
TOOLS = AGENT / "tools.json"
CHECKS = "T4-003,T1-004,T4-012,X-019"
VARIANTS = {"original": True, "fixed": False}


def record(variant: str) -> dict:
    """One run of the probe `canon` ("Please refill my metformin prescription."), in the demo's native shape."""
    result = RefillAgent(buggy=VARIANTS[variant]).run(PROBES["canon"])
    name = "refill_bot_buggy" if VARIANTS[variant] else "refill_bot"
    return {"agent": name, "probe": "canon", "rep": 0, "input": PROBES["canon"],
            "trace": result["log"], "output": result["output"]}


def to_otlp(native: Path, out: Path) -> int:
    return agentest_cli(["std", "import", str(native), "--map", str(MAP), "--tools", str(TOOLS),
                         "--service", "refill_bot", "--out", str(out)])


def notify_recipients(row: dict) -> list[str]:
    return [json.loads(line.split(" ", 2)[2])["to"] for line in row["trace"] if line.startswith("CALL notify ")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=sorted(VARIANTS), default="original")
    ap.add_argument("--no-write", action="store_true", help="do not update the files under traces/")
    a = ap.parse_args()
    row = record(a.variant)
    out = HERE / "traces"
    if a.no_write:
        import tempfile
        out = Path(tempfile.mkdtemp(prefix="failure-lab-002-"))
    out.mkdir(exist_ok=True)
    native = out / f"{a.variant}.native.jsonl"
    native.write_text(json.dumps(row) + "\n", encoding="utf-8")
    otlp = out / f"{a.variant}.otlp.jsonl"
    if to_otlp(native, otlp) != 0:
        return 1
    print(f"variant: {a.variant}")
    print(f"answer: {row['output']['final']}")
    print(f"notify recipients: {notify_recipients(row)}")
    for check in agentest.run(otlp, card=CARD, tools=TOOLS, ids=CHECKS):
        print(check.id, check.status, check.detail)
    return 0


if __name__ == "__main__":
    sys.exit(main())
