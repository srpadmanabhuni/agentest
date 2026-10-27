"""Score regex / embedding only / SLM only / hybrid on the cases from one oracle (live or replayed cache)."""

from __future__ import annotations

import json
from pathlib import Path

from cases import CASES

from agentest.standards import oracle, rules

HERE = Path(__file__).resolve().parent
TASK = oracle.load_task("break-glass")
EMBED_ID = "llamacpp:bge-m3-Q4_K_M.gguf"
SLM_ID = "http:Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M"
CACHE = HERE / "oracle-cache.jsonl"


def replay() -> oracle.Oracle:
    return oracle.Oracle(oracle.backend("replay", EMBED_ID), oracle.backend("replay", SLM_ID), CACHE, offline=True)


def _args(a: dict) -> str:
    return json.dumps(a, ensure_ascii=False, sort_keys=True, default=str)  # what T3-012 passes (rules._dumps)


def evaluate(o: oracle.Oracle, warm: bool = False) -> list[dict]:
    rows = []
    for tool, args, truth, kind in CASES:
        text = f"{tool} {_args(args)}"
        s = o.scores(TASK, text)
        emb = max(s, key=s.get) == TASK.positive
        slm = o.ask(TASK, text) == TASK.positive if warm or _cached_slm(o, text) else None
        hyb = o.classify(TASK, text)
        rows.append({"tool": tool, "text": text, "truth": truth, "kind": kind,
                     "regex": bool(rules.BREAKGLASS_RX.search(_args(args))), "embedding": emb, "slm": slm,
                     "hybrid": hyb.label == TASK.positive, "via": hyb.via, "margin": hyb.margin})
    return rows


def _cached_slm(o: oracle.Oracle, text: str) -> bool:
    try:
        o.ask(TASK, text)
        return True
    except oracle.OracleUnavailable:
        return False


def summary(rows: list[dict]) -> dict:
    out = {}
    for m in ("regex", "embedding", "slm", "hybrid"):
        rs = [r for r in rows if r[m] is not None]
        out[m] = {"correct": sum(r[m] == r["truth"] for r in rs), "of": len(rs),
                  "false_positive": sum(r[m] and not r["truth"] for r in rs), "false_negative": sum(r["truth"] and not r[m] for r in rs)}
    return out


def table(rows: list[dict]) -> str:
    mark = lambda r, m: "-" if r[m] is None else ("ok" if r[m] == r["truth"] else ("**FP**" if r[m] else "**FN**"))  # noqa: E731
    lines = ["| kind | tool call | truth | regex | embedding | SLM | hybrid (via) |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['kind']} | `{r['text'][:70]}` | {'break-glass' if r['truth'] else 'routine'} | {mark(r, 'regex')} | "
                     f"{mark(r, 'embedding')} | {mark(r, 'slm')} | {mark(r, 'hybrid')} ({r['via']}) |")
    return "\n".join(lines)


if __name__ == "__main__":
    rows = evaluate(replay())
    print(table(rows))
    print(json.dumps(summary(rows), indent=1))
