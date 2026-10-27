"""``agentest std``: the standards-based engine (validate, run, regress, export, gen, catalog, import, serve)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _otlp_agent(args):
    """An ad-hoc agent from plain OTLP files (+ optional AgentCard / MCP tools), staged in a temp directory."""
    import shutil
    import tempfile

    from agentest.standards import metadata

    d = Path(tempfile.mkdtemp(prefix="agentest-otlp-")) / "otlp_agent"
    d.mkdir()
    for n, f in enumerate(args.otlp):
        suf = Path(f).suffix
        shutil.copy(f, d / (f"{n:03d}{suf}" if suf in (".pb", ".binpb") else f"{n:03d}.otlp.json{'l' if suf == '.jsonl' else ''}"))
    if args.card:
        shutil.copy(args.card, d / "agent-card.json")
    if args.tools:
        shutil.copy(args.tools, d / "tools.json")
    return {"otlp_agent": metadata.load(d)}


def _import(args) -> int:
    """Native logs -> OTLP/JSON traces with a pure-data mapping (and an optional mapping function)."""
    from agentest.standards import importers, metadata

    if not args.inputs:
        print("std import: give one or more native log files")
        return 2
    mapping = json.loads(Path(args.map).read_text()) if args.map else {}
    if args.dialect:
        mapping["dialect"] = args.dialect
    if not mapping.get("dialect"):
        print(f"std import: --dialect or a mapping file with 'dialect' is required ({', '.join(sorted(importers.DIALECTS))}, file:my.py)")
        return 2
    is_write = None
    if args.tools:
        tl = json.loads(Path(args.tools).read_text())
        stub = metadata.Agent("import", Path("."), {}, {t["name"]: t for t in tl.get("tools", [])})
        is_write = stub.is_write
    raws = [r for f in args.inputs for r in importers.read_native(f)]
    service = args.service or (raws[0].get("agent") if raws and raws[0].get("agent") else "agent")
    docs = importers.to_docs(raws, mapping, service, is_write, base=Path(args.map).parent if args.map else Path.cwd())
    text = "".join(json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n" for d in docs)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text)
        print(f"wrote {len(docs)} OTLP/JSON traces to {args.out}")
    else:
        print(text, end="")
    return 0


def _write(args, text: str) -> None:
    if args.out:
        Path(args.out).write_text(text)
    else:
        print(text)



def _semconv_notes(ags: dict, out) -> None:
    """Report traces whose OTel schema URL declares a semantic-convention version that is not the pinned one."""
    from agentest.standards import runner
    from agentest.standards.otel import declared_semconv, semconv, semconv_status

    pinned = semconv()["pinned"]["semconv"]
    for k, a in ags.items():
        seen = {v for d in runner.otlp_docs(a) for v in declared_semconv(d)}
        for v in sorted(seen - {pinned}):
            st = semconv_status(v)
            how = {"newer": f"newer than the pinned {pinned}: attributes added since are not mapped",
                   "unknown": "older than every mapping table: attributes may be missed"}.get(st, f"mapped by the {st!r} table in semconv.yaml")
            print(f"{k}: traces declare semantic conventions {v} ({how})", file=out)

def cmd_std(args) -> int:
    from agentest.standards import ext, inputs, judge, metadata, reports, runner

    if any(getattr(args, k, None) for k in ("judge", "judge_model", "judge_cache", "judge_offline")):
        judge.configure(getattr(args, "judge", None), getattr(args, "judge_model", None), None, getattr(args, "judge_cache", None),
                        True if getattr(args, "judge_offline", False) else None)

    ext.configure(ext.read_config(getattr(args, "config", None)), Path(args.config).parent if getattr(args, "config", None) else None)
    if getattr(args, "rules_dir", None):
        ext.load_plugins(args.rules_dir)
    if args.action == "serve":
        from agentest.standards.serve import serve

        return serve(Path(args.out or "otlp-in"), args.host, args.port, args.max_requests)
    if args.action == "import":
        return _import(args)
    if args.action == "catalog":
        _write(args, reports.catalog_csv() if args.format == "csv" else json.dumps(reports.catalog_rows(), indent=1, ensure_ascii=False))
        return 0
    ags = _otlp_agent(args) if getattr(args, "otlp", None) else metadata.load_all(Path(args.agents) if args.agents else None)
    if args.agent:
        if args.agent not in ags:
            print(f"unknown agent {args.agent!r}")
            return 2
        ags = {args.agent: ags[args.agent]}
    if args.action in ("validate", "run"):
        _semconv_notes(ags, sys.stdout if args.action == "validate" else sys.stderr)
    if args.action == "validate":
        bad = {k: e for k, a in ags.items() if (e := metadata.validate(a))}
        for k, e in bad.items():
            print(f"{k}: " + "; ".join(e))
        print(f"{len(ags) - len(bad)}/{len(ags)} agents have valid AgentCard + MCP tools metadata")
        return 1 if bad else 0
    if args.action == "gen":
        print(json.dumps({k: {**inputs.generate(a), **inputs.counterfactuals(a)} for k, a in ags.items()}, indent=1, ensure_ascii=False))
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
    cov = None
    if args.action == "run":
        from agentest.standards import instrumentation

        try:
            cov = instrumentation.gate(res, getattr(args, "max_na", None), {k: runner.runs(a) for k, a in ags.items()})
        except ValueError as e:
            print(str(e))
            return 2
    if getattr(args, "ids", None) and args.action == "run":
        want = {x.strip() for x in args.ids.split(",") if x.strip()}
        unknown = sorted(want - set(next(iter(res.values()), {})))
        if unknown:
            print(f"unknown test IDs: {', '.join(unknown)}")
            return 2
        res = {k: {i: c for i, c in row.items() if i in want} for k, row in res.items()}
    if getattr(args, "emit_otlp", None):
        from agentest.standards.otel import root_ids

        links = {k: [x for d in runner.otlp_docs(a) for x in root_ids(d)] for k, a in ags.items()}
        Path(args.emit_otlp).write_text(json.dumps(reports.to_otlp_verdicts(res, args.mode, links)) + "\n")
    if args.action == "regress":
        g = runner.regress(res, runner.baseline())
        print(json.dumps(g["tally"], indent=1))
        if args.json:
            Path(args.json).write_text(json.dumps(g, indent=1))
        floor = getattr(args, "floor", None)
        if floor is not None:
            t = g["tally"]
            # without a judge, semantic cells are not-assessed: they count toward the floor only as 'not asked', never as a pass
            got = t["caught"] + (t["missed_as_not_assessed"] if judge.active() is None else 0)
            print(f"regression floor {floor}: {got} ({t['caught']} caught" + (f" + {t['missed_as_not_assessed']} not assessed" if judge.active() is None else "") + ")")
            return 0 if got >= floor else 1
        return 0
    fmt = getattr(args, "format", None)
    if fmt:
        out = {"json": lambda: json.dumps(reports.to_versioned_json(res, args.mode, cov), indent=1),
               "junit": lambda: reports.to_junit(res, args.mode, cov), "sarif": lambda: json.dumps(reports.to_sarif(res, args.mode, cov), indent=1),
               "md": lambda: reports.to_markdown(res, args.mode), "html": lambda: reports.to_html(res, args.mode),
               "csv": lambda: "agent,id,status,detail\n" + "".join(f'{a},{i},{c["status"]},"{c["detail"].replace(chr(34), chr(39))}"\n' for a, row in res.items() for i, c in row.items())}[fmt]()
        if not args.out:  # report to stdout, so it can be piped
            print(out)
            _coverage_notes(cov, sys.stderr)
            return 1 if (args.strict and any(c["status"] == "fail" for row in res.values() for c in row.values())) or (cov and not cov["ok"]) else 0
        Path(args.out).write_text(out)
    tot = {s: sum(c["status"] == s for row in res.values() for c in row.values()) for s in ("pass", "fail", "n/a", "not-assessed")}
    for k, row in res.items():
        f = sorted(i for i, c in row.items() if c["status"] == "fail")
        print(f"{k}: {sum(c['status'] == 'pass' for c in row.values())} pass, {len(f)} fail" + (f" ({', '.join(f)})" if f else ""))
    n_ids = len(next(iter(res.values()), {}))
    from agentest.standards import judge

    jd = judge.describe()["judge"]
    print(f"total: {tot['pass']} pass, {tot['fail']} fail, {tot['n/a']} n/a, {tot['not-assessed']} not assessed over {len(res)} agents x {n_ids} IDs ({args.mode}); "
          f"judge: {(jd['model'] + ' @ ' + jd['endpoint']) if jd else 'none (semantic checks not assessed)'}")
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1))
    _coverage_notes(cov, sys.stdout)
    return 1 if (args.strict and tot["fail"]) or (cov and not cov["ok"]) else 0


def _coverage_notes(cov: dict | None, out) -> None:
    """Print the instrumentation-coverage gate: one line per failing agent, then the gate result."""
    if not cov:
        return
    from agentest.standards import instrumentation

    for a in cov["failing"]:
        print("instrumentation coverage FAIL " + instrumentation.message(a, cov["agents"][a]), file=out)
    worst = max(cov["agents"].values(), key=lambda c: c["na_share"], default=None)
    print(f"instrumentation coverage: {'ok' if cov['ok'] else 'FAIL'} ({len(cov['failing'])} of {len(cov['agents'])} agent(s) above "
          f"max n/a share {cov['max_na_share']:.0%}" + (f"; highest {worst['na_share']:.0%}" if worst else "") + ")", file=out)
