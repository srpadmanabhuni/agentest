"""``agentest std``: the v3.0.0 standards-based engine."""

from __future__ import annotations

import json
from pathlib import Path


def _otlp_agent(args):
    """An ad-hoc agent from plain OTLP files (+ optional AgentCard / MCP tools), staged in a temp directory."""
    import shutil
    import tempfile

    from agentest.standards import metadata

    d = Path(tempfile.mkdtemp(prefix="agentest-otlp-")) / "otlp_agent"
    d.mkdir()
    for n, f in enumerate(args.otlp):
        shutil.copy(f, d / f"{n:03d}.otlp.json{'l' if str(f).endswith('.jsonl') else ''}")
    if args.card:
        shutil.copy(args.card, d / "agent-card.json")
    if args.tools:
        shutil.copy(args.tools, d / "tools.json")
    a = metadata.load(d)
    a.adapter = dict(metadata.OTLP_ONLY)
    return {"otlp_agent": a}


def _write(args, text: str) -> None:
    if args.out:
        Path(args.out).write_text(text)
    else:
        print(text)


def cmd_std(args) -> int:
    from agentest.standards import ext, inputs, metadata, reports, runner

    ext.configure(ext.read_config(getattr(args, "config", None)), Path(args.config).parent if getattr(args, "config", None) else None)
    if getattr(args, "rules_dir", None):
        ext.load_plugins(args.rules_dir)
    if args.action == "catalog":
        _write(args, reports.catalog_csv() if args.format == "csv" else json.dumps(reports.catalog_rows(), indent=1, ensure_ascii=False))
        return 0
    ags = _otlp_agent(args) if getattr(args, "otlp", None) else metadata.load_all(Path(args.agents) if args.agents else None)
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
    fmt = getattr(args, "format", None)
    if fmt:
        out = {"json": lambda: json.dumps(reports.to_versioned_json(res, args.mode), indent=1),
               "junit": lambda: reports.to_junit(res, args.mode), "sarif": lambda: json.dumps(reports.to_sarif(res, args.mode), indent=1),
               "md": lambda: reports.to_markdown(res, args.mode), "html": lambda: reports.to_html(res, args.mode),
               "csv": lambda: "agent,id,status,detail\n" + "".join(f'{a},{i},{c["status"]},"{c["detail"].replace(chr(34), chr(39))}"\n' for a, row in res.items() for i, c in row.items())}[fmt]()
        if args.out:
            Path(args.out).write_text(out)
    tot = {s: sum(c["status"] == s for row in res.values() for c in row.values()) for s in ("pass", "fail", "n/a")}
    for k, row in res.items():
        f = sorted(i for i, c in row.items() if c["status"] == "fail")
        print(f"{k}: {sum(c['status'] == 'pass' for c in row.values())} pass, {len(f)} fail" + (f" ({', '.join(f)})" if f else ""))
    n_ids = len(next(iter(res.values()), {}))
    print(f"total: {tot['pass']} pass, {tot['fail']} fail, {tot['n/a']} n/a over {len(res)} agents x {n_ids} IDs ({args.mode})")
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1))
    return 1 if args.strict and tot["fail"] else 0
