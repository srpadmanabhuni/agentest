"""Run the 46 opt-in checks on the locked labelled set and write predictions (one jsonl row per scenario x check).

Refuses to run if any data file no longer matches MANIFEST.json (the lock).  Usage: python run_eval.py OUT.jsonl
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

from agentest.standards import GOV_EXT  # noqa: E402
from agentest.standards.metadata import Agent  # noqa: E402
from agentest.standards.otel import from_otlp  # noqa: E402
from agentest.standards.rules import evaluate  # noqa: E402


def verify() -> dict:
    man = json.loads((HERE / "MANIFEST.json").read_text())
    for rel, h in man["files"].items():
        if hashlib.sha256((HERE / rel).read_bytes()).hexdigest() != h:
            sys.exit(f"LOCK BROKEN: {rel} differs from MANIFEST.json")
    return man


def main(out: str) -> None:
    man = verify()
    std = json.loads((HERE / "tools_std.json").read_text())
    rows = []
    for f in sorted((HERE / "data").glob("*.jsonl.gz")):
        for line in gzip.open(f, "rt", encoding="utf-8"):
            s = json.loads(line)
            tools = s.get("tools_full") or {**std, **(s.get("tools_patch") or {})}
            gov = s.get("gov") or {}
            card = {"name": "eval", "skills": [], "capabilities": {"extensions": [{"uri": GOV_EXT, "params": gov}] if gov else []}}
            agent = Agent("eval", HERE, card, tools, gov)
            runs = [from_otlp(json.loads(json.dumps(d))) for d in s["traces"]]
            for cid in s["check_ids"]:
                try:
                    r = evaluate(agent, runs, ids=[cid])[cid]
                    status, detail = r.status, r.detail
                except Exception as e:  # recorded, never hidden
                    status, detail = "error", f"{type(e).__name__}: {e}"
                rows.append({"scenario_id": s["scenario_id"], "check_id": cid, "status": status, "detail": detail})
    Path(out).write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    print(f"{len(rows)} predictions; lock {man['lock_hash'][:12]}")


if __name__ == "__main__":
    main(sys.argv[1])
