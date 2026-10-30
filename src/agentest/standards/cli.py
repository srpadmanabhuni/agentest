"""``agentest std``: the standards-based engine (validate, run, regress, export, gen, catalog, import, serve)."""

from __future__ import annotations

import json
import os
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


def _lint(args) -> int:
    import json

    from agentest.standards import lint

    if not args.inputs:
        print("lint: give one or more OTLP trace files", file=sys.stderr)
        return 2
    args.otlp = list(args.inputs)
    rep = lint.lint(_otlp_agent(args)["otlp_agent"], mode=args.mode)
    if args.json:
        Path(args.json).write_text(json.dumps(rep, indent=1) + "\n")
    print(lint.text(rep))
    return 0


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
    try:
        raws = [r for f in args.inputs for r in importers.read_native(f)]
    except (OSError, ValueError) as e:
        print(f"std import: {e}")
        return 2
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

def _governance(args) -> int:
    """v3.5: derive governance-extension params from MCP annotations or a LangGraph / AutoGen / CrewAI config."""
    from agentest.standards import GOV_EXT, governance

    if not args.gov_from or not args.inputs:
        print("governance: needs --from {mcp,langgraph,autogen,crewai} and an input file", file=sys.stderr)
        return 2
    params, prov = {}, {}
    for f in args.inputs:
        p, pv = governance.CONVERTERS[args.gov_from](governance.load_source(f))
        params, prov = governance.merge(params, p), {**pv, **prov}
    if args.tools:
        p, pv = governance.from_mcp(governance.load_source(args.tools))
        params, prov = governance.merge(params, p), {**pv, **prov}
    for k, why in sorted(prov.items()):
        print(f"derived {k}: {why}", file=sys.stderr)
    if args.card:
        card = json.loads(Path(args.card).read_text())
        exts = card.setdefault("capabilities", {}).setdefault("extensions", [])
        cur = next((e for e in exts if e.get("uri") == GOV_EXT), None)
        if cur is None:
            exts.append(governance.extension(params))
        else:
            cur["params"] = governance.merge(cur.get("params") or {}, params)
        _write(args, json.dumps(card, indent=2, ensure_ascii=False))
    else:
        _write(args, json.dumps(governance.extension(params), indent=2, ensure_ascii=False))
    return 0


def cmd_std(args) -> int:
    from agentest.standards import ext, inputs, judge, metadata, reports, runner

    if any(getattr(args, k, None) for k in ("judge", "judge_model", "judge_cache", "judge_offline")):
        judge.configure(getattr(args, "judge", None), getattr(args, "judge_model", None), None, getattr(args, "judge_cache", None),
                        True if getattr(args, "judge_offline", False) else None)
    if any(getattr(args, k, None) for k in ("judge2", "judge2_model", "judge2_cache", "judge2_offline")):
        judge.configure2(getattr(args, "judge2", None), getattr(args, "judge2_model", None), getattr(args, "judge2_cache", None),
                         True if getattr(args, "judge2_offline", False) else None)

    ext.configure(ext.read_config(getattr(args, "config", None)), Path(args.config).parent if getattr(args, "config", None) else None)
    if getattr(args, "rules_dir", None):
        ext.load_plugins(args.rules_dir)
    if args.action == "lint":
        return _lint(args)
    if args.action == "serve":
        from agentest.standards.serve import serve

        return serve(Path(args.out or "otlp-in"), args.host, args.port, args.max_requests)
    if args.action == "import":
        return _import(args)
    if args.action == "governance":
        return _governance(args)
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
    if getattr(args, "run_env", None):
        os.environ["AGENTEST_RUN_ENV"] = args.run_env
    from agentest.standards import trust

    blind = bool(getattr(args, "blind", False))
    key = trust.load_key(getattr(args, "trace_key_file", None))
    if blind or getattr(args, "require_signed", False):
        refused = runner.unsigned(ags, key)
        if refused:
            for k, why in refused.items():
                print(f"refused (unsigned trace): {k}: {why[0]}" + (f" (+{len(why) - 1} more)" if len(why) > 1 else ""))
            print(f"{len(refused)} agent(s) refused: blind mode requires traces signed by the harness key")
            return 2
    res = runner.to_json(runner.run_all(ags, mode=args.mode, blind=blind, key=key))
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
    explain = bool(getattr(args, "explain", False))
    shown = res
    if args.action == "run" and (explain or getattr(args, "format", None) in ("md", "html")):
        from agentest.standards import guidance

        shown = guidance.annotate(res, {k: runner.runs(a) for k, a in ags.items()})
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
        g = shown if explain else res
        out = {"json": lambda: json.dumps(reports.to_versioned_json(g, args.mode, cov), indent=1),
               "junit": lambda: reports.to_junit(g, args.mode, cov), "sarif": lambda: json.dumps(reports.to_sarif(g, args.mode, cov), indent=1),
               "md": lambda: reports.to_markdown(shown, args.mode), "html": lambda: reports.to_html(shown, args.mode),
               "csv": lambda: reports.to_csv(g)}[fmt]()
        if not args.out:  # report to stdout, so it can be piped
            print(out)
            _coverage_notes(cov, sys.stderr)
            return 1 if (args.strict and any(c["status"] == "fail" for row in res.values() for c in row.values())) or (cov and not cov["ok"]) else 0
        Path(args.out).write_text(out)
    tot = {s: sum(c["status"] == s for row in res.values() for c in row.values()) for s in ("pass", "fail", "n/a", "not-assessed")}
    for k, row in res.items():
        f = sorted(i for i, c in row.items() if c["status"] == "fail")
        print(f"{k}: {sum(c['status'] == 'pass' for c in row.values())} pass, {len(f)} fail" + (f" ({', '.join(f)})" if f else ""))
        if explain:
            from agentest.standards import guidance

            for i, c in sorted(shown[k].items()):
                if c["status"] == "fail" and c.get("guide"):
                    print(f"  {i} fail: {guidance.text(c['guide'])}")
            need: dict = {}
            for c in shown[k].values():
                if c["status"] == "n/a" and c.get("guide"):
                    need[c["guide"]["missing"]] = need.get(c["guide"]["missing"], 0) + 1
            for f_, n in sorted(need.items(), key=lambda kv: -kv[1])[:5]:
                print(f"  n/a x{n}: missing {f_}")
    n_ids = len(next(iter(res.values()), {}))
    from agentest.standards import judge

    jd = judge.describe()["judge"]
    print(f"total: {tot['pass']} pass, {tot['fail']} fail, {tot['n/a']} n/a, {tot['not-assessed']} not assessed over {len(res)} agents x {n_ids} IDs ({args.mode}); "
          f"judge: {(jd['model'] + ' @ ' + jd['endpoint']) if jd else 'none (semantic checks not assessed)'}")
    if args.json:
        Path(args.json).write_text(json.dumps(shown if explain else res, indent=1))
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
