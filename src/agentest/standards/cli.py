"""``agentest std``: the v3.0.0-dev standards-based engine."""

from __future__ import annotations

import json
from pathlib import Path


def cmd_std(args) -> int:
    from agentest.standards import inputs, metadata, runner

    ags = metadata.load_all(Path(args.agents) if args.agents else None)
    if args.agent:
        if args.agent not in ags:
            print(f"unknown agent {args.agent!r}")
            return 2
        ags = {args.agent: ags[args.agent]}
    if args.action == "validate":
        bad = {k: e for k, a in ags.items() if (e := metadata.validate(a))}
        for k, e in bad.items():
            print(f"{k}: " + "; ".join(e))
        print(f"{len(ags) - len(bad)}/{len(ags)} agents have valid AgentCard + MCP tools metadata")
        return 1 if bad else 0
    if args.action == "gen":
        print(json.dumps({k: inputs.generate(a) for k, a in ags.items()}, indent=1))
        return 0
    if args.action == "export":
        out = Path(args.out or "otlp")
        out.mkdir(parents=True, exist_ok=True)
        n = 0
        for k, a in ags.items():
            docs = runner.otlp_docs(a)
            (out / f"{k}.otlp.jsonl").write_text("".join(json.dumps(d) + "\n" for d in docs))
            n += len(docs)
        print(f"wrote {n} OTLP/JSON traces for {len(ags)} agents to {out}/")
        return 0
    res = runner.to_json(runner.run_all(ags, mode=args.mode))
    if args.action == "regress":
        g = runner.regress(res, runner.baseline())
        print(json.dumps(g["tally"], indent=1))
        if args.json:
            Path(args.json).write_text(json.dumps(g, indent=1))
        return 0
    tot = {s: sum(c["status"] == s for row in res.values() for c in row.values()) for s in ("pass", "fail", "n/a")}
    for k, row in res.items():
        f = sorted(i for i, c in row.items() if c["status"] == "fail")
        print(f"{k}: {sum(c['status'] == 'pass' for c in row.values())} pass, {len(f)} fail" + (f" ({', '.join(f)})" if f else ""))
    print(f"total: {tot['pass']} pass, {tot['fail']} fail, {tot['n/a']} n/a over {len(res)} agents x 130 IDs ({args.mode})")
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1))
    return 1 if args.strict and tot["fail"] else 0
