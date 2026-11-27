"""Run the refund workflow with openai-agents 0.26.0, record it, and judge it with agentest.

    python examples/failure-lab/001-refund-timeout-retry/reproduce.py --variant original
    python examples/failure-lab/001-refund-timeout-retry/reproduce.py --variant fixed

Writes traces/<variant>.run.json (the SDK items) and traces/<variant>.otlp.json (the agentest trace).
No API key and no network: the model is scripted (see refund_agent.py).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_AGENTS_DISABLE_TRACING", "1")  # no trace export to a remote service
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from refund_agent import run_scenario  # noqa: E402
from to_trace import TOOLS, build_trace  # noqa: E402

import agentest  # noqa: E402

CHECKS = "T2-003,T1-006,T1-011"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["original", "fixed"], default="original")
    ap.add_argument("--no-write", action="store_true", help="do not update the files under traces/")
    a = ap.parse_args()
    run = run_scenario(a.variant)
    doc = build_trace(run)
    if not a.no_write:
        (HERE / "traces").mkdir(exist_ok=True)
        (HERE / "traces" / f"{a.variant}.run.json").write_text(json.dumps(run, indent=1, default=str) + "\n", encoding="utf-8")
        (HERE / "traces" / f"{a.variant}.otlp.json").write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"variant: {a.variant}")
    print(f"answer: {run['answer']}")
    print(f"submit_refund calls: {sum(1 for i in run['items'] if i.get('name') == 'submit_refund')}")
    print(f"refunds created: {len(run['refunds'])} {[r['refund_ticket'] for r in run['refunds']]}")
    result = agentest.run(doc, tools=str(TOOLS), ids=CHECKS)
    for cid in CHECKS.split(","):
        check = result[cid]
        print(check.id, check.status, check.detail)
    return 0


if __name__ == "__main__":
    sys.exit(main())
