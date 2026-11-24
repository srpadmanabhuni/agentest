"""``agentest std``: the standards-based engine (validate, run, regress, export, gen, catalog, import, serve, diff)."""
# Ref: internal design (docs/standards/DEVELOPER-GUIDE.md); output formats cite their specs in reports.py, trace input in otel.py.

from __future__ import annotations

import json
import sys
from pathlib import Path


class StdInputError(ValueError):
    """``std run --otlp`` was given a path or JSON document it cannot stage.

    Only this input check raises it. Rule failures and other reader errors are left alone.
    """


class UnknownTestIds(ValueError):
    """``std run --ids`` named a test id or class this build does not know."""

    def __init__(self, unknown: list[str]):
        self.unknown = list(unknown)
        super().__init__(
            f"unknown test IDs: {', '.join(self.unknown)}. "
            "List catalogue IDs with: agentest list. "
            "List opt-in responsible-AI additions with: agentest list --opt-in"
        )


def restrict_ids(res: dict, ags: dict, ids: str, mode: str) -> dict:
    """Apply a ``std run --ids`` selection to a finished verdict map.

    The map is the object ``--json`` writes. Opt-in ids are judged and merged, then every
    check outside the selection is dropped. Unknown ids raise ``UnknownTestIds``.
    """
    from agentest.standards import runner
    from agentest.standards.catalog import ALL_IDS, NEW_TEST_IDS, RAI_ADDITION_IDS
    from agentest.standards.rules import RULES

    default_ids = set(ALL_IDS) | {k for k in RULES if k not in ALL_IDS and k not in RAI_ADDITION_IDS and k not in NEW_TEST_IDS}
    from agentest.standards.packs import pack_rules

    pack_ids = set(pack_rules())  # opt-in extension packs (MA, PV, RT, BF, EX, DL): never in the default run
    known = default_ids | set(RAI_ADDITION_IDS) | set(NEW_TEST_IDS) | pack_ids
    classes = {f"T{i}" for i in range(1, 8)} | {"X"}
    want, unknown = set(), []
    for item in (x.strip() for x in ids.split(",") if x.strip()):
        if item == "NT":
            want.update(NEW_TEST_IDS)  # every opt-in New test
            try:
                from agentest.standards.new_tests.b3 import PHASE1_SHIPPED
            except ImportError:
                PHASE1_SHIPPED = ()
            want.update(PHASE1_SHIPPED)  # T1-020, T1-021 when batch 3 is present
        elif item in classes:
            # Class shorthand stays on the default set (+ plugins), not the opt-in additions.
            want.update(i for i in default_ids if i.startswith(item + "-"))
        elif item in known:
            want.add(item)
        else:
            unknown.append(item)
    unknown = sorted(set(unknown))
    if unknown:
        raise UnknownTestIds(unknown)
    rai_want = sorted(want & (set(RAI_ADDITION_IDS) | set(NEW_TEST_IDS) | pack_ids))
    if rai_want:
        extra = runner.to_json(runner.run_all(ags, mode=mode, ids=rai_want))
        for k, row in extra.items():
            res.setdefault(k, {}).update(row)
    return {k: {i: c for i, c in row.items() if i in want} for k, row in res.items()}


def format_run_summary(res: dict, mode: str) -> str:
    """The summary ``agentest std run`` prints for a finished run."""
    lines = []
    for k, row in res.items():
        failed = sorted(i for i, c in row.items() if c["status"] == "fail")
        n_pass = sum(c["status"] == "pass" for c in row.values())
        line = f"{k}: {n_pass} pass, {len(failed)} fail"
        if failed:
            line += f" ({', '.join(failed)})"
        lines.append(line)
    tot = {s: sum(c["status"] == s for row in res.values() for c in row.values()) for s in ("pass", "fail", "n/a")}
    n_ids = len(next(iter(res.values()), {}))
    lines.append(f"total: {tot['pass']} pass, {tot['fail']} fail, {tot['n/a']} n/a over {len(res)} agents x {n_ids} IDs ({mode})")
    return "\n".join(lines)


def _require_file(path) -> Path:
    p = Path(path)
    if not p.is_file():
        raise StdInputError(f"{p} is not a file; pass an existing OTLP/JSON or JSONL trace, for example a path under agents/<id>/traces/")
    return p


def _require_json(path: Path) -> None:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise StdInputError(f"{path} is not valid JSON ({e.msg}, line {e.lineno})") from None


def _otlp_agent(args):
    """An ad-hoc agent from plain OTLP files (+ optional AgentCard / MCP tools), staged in a temp directory."""
    import shutil
    import tempfile

    from agentest.standards import metadata
    from agentest.standards.otel import read_otlp_file

    root = Path(tempfile.mkdtemp(prefix="agentest-otlp-"))
    d = root / "otlp_agent"
    d.mkdir()
    try:
        for n, f in enumerate(args.otlp):
            src = _require_file(f)
            suf = src.suffix
            dest = d / (f"{n:03d}{suf}" if suf in (".pb", ".binpb") else f"{n:03d}.otlp.json{'l' if suf == '.jsonl' else ''}")
            shutil.copy(src, dest)
            if suf not in (".pb", ".binpb"):
                try:
                    read_otlp_file(dest)
                except json.JSONDecodeError as e:
                    raise StdInputError(f"{src} is not valid JSON ({e.msg}, line {e.lineno})") from None
        if args.card:
            src = _require_file(args.card)
            _require_json(src)
            shutil.copy(src, d / "agent-card.json")
        if args.tools:
            src = _require_file(args.tools)
            _require_json(src)
            shutil.copy(src, d / "tools.json")
        return {"otlp_agent": metadata.load(d)}
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def _import(args) -> int:
    """Native logs -> OTLP/JSON traces with a pure-data mapping (and an optional mapping function)."""
    from agentest.standards import importers

    if not args.inputs:
        print("std import: give one or more native log files")
        return 2
    if args.map:
        try:
            mapping = json.loads(Path(args.map).read_text(encoding="utf-8"))
        except FileNotFoundError:
            print(f"std import: {args.map} not found")
            return 2
        except json.JSONDecodeError as e:
            print(f"std import: {args.map} is not valid JSON ({e.msg}, line {e.lineno})")
            return 2
        if not isinstance(mapping, dict):
            print("std import: mapping file must be a JSON object")
            return 2
    else:
        mapping = {}
    if args.dialect:
        mapping["dialect"] = args.dialect
    if getattr(args, "trace_format", False):
        mapping["trace_format"] = importers.TRACE_FORMAT_VERSION
    if not mapping.get("dialect"):
        print(f"std import: --dialect or a mapping file with 'dialect' is required ({', '.join(sorted(importers.DIALECTS))}, file:my.py)")
        return 2
    try:
        is_write = importers.is_write_from_tools(args.tools) if args.tools else None
        raws = [r for f in args.inputs for r in importers.read_native(f)]
        service = args.service or (raws[0].get("agent") if raws and raws[0].get("agent") else "agent")
        docs = importers.to_docs(raws, mapping, service, is_write, base=Path(args.map).parent if args.map else Path.cwd())
    except importers.NativeLogError as e:
        print(f"std import: {e}")
        return 2
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



def _diff(args) -> int:
    """Compare two saved ``std run --json`` files. Exit 1 with ``--fail-on-new-fail`` when something newly fails."""
    from agentest.standards.verdict_diff import VerdictFileError, diff_verdicts, load_verdicts, render_diff

    paths = list(getattr(args, "inputs", None) or [])
    if len(paths) != 2:
        print("std diff: give two verdict files: agentest std diff OLD.json NEW.json")
        return 2
    try:
        report = diff_verdicts(load_verdicts(paths[0]), load_verdicts(paths[1]))
    except VerdictFileError as e:
        print(f"std diff: {e}")
        return 2
    text = render_diff(report)
    if getattr(args, "json", None):
        Path(args.json).write_text(json.dumps(report, indent=1) + "\n")
    print(text)
    if getattr(args, "fail_on_new_fail", False) and report["newly_failing"]:
        return 1
    return 0


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
    from agentest.standards import ext, inputs, metadata, reports, runner

    ext.configure(ext.read_config(getattr(args, "config", None)), Path(args.config).parent if getattr(args, "config", None) else None)
    if getattr(args, "rules_dir", None):
        ext.load_plugins(args.rules_dir)
    if args.action == "diff":
        return _diff(args)
    if args.action == "serve":
        from agentest.standards.serve import serve

        return serve(Path(args.out or "otlp-in"), args.host, args.port, args.max_requests)
    if args.action == "import":
        return _import(args)
    if args.action == "catalog":
        _write(args, reports.catalog_csv() if args.format == "csv" else json.dumps(reports.catalog_rows(), indent=1, ensure_ascii=False))
        return 0
    if getattr(args, "otlp", None):
        try:
            ags = _otlp_agent(args)
        except StdInputError as e:
            print(f"std {args.action}: {e}")
            return 2
    else:
        ags = metadata.load_all(Path(args.agents) if args.agents else None)
    if args.agent:
        if args.agent not in ags:
            print(f"unknown agent {args.agent!r}; list folders under agents/ (or --agents). See agentest --help or the README first-run.")
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
    sel = getattr(args, "ids", None) or ""
    if args.action == "run" and getattr(args, "pack", None):
        from agentest.local import packs

        for name in [x.strip().lower() for x in args.pack.split(",") if x.strip()]:
            ids = packs().get(name)
            if ids is None:
                print(f"unknown pack {name!r}; see 'agentest list --packs'")
                return 2
            sel = ",".join([x for x in (sel, *ids) if x])
    if sel and args.action == "run":
        try:
            res = restrict_ids(res, ags, sel, args.mode)
        except UnknownTestIds as e:
            print(e)
            return 2
    if getattr(args, "emit_otlp", None):
        from agentest.standards.otel import root_ids

        links = {k: [x for d in runner.otlp_docs(a) for x in root_ids(d)] for k, a in ags.items()}
        Path(args.emit_otlp).write_text(json.dumps(reports.to_otlp_verdicts(res, args.mode, links)) + "\n")
    if args.action == "regress":
        g = runner.regress(res, runner.baseline())
        print(json.dumps(g["tally"], indent=1))
        if args.json:
            Path(args.json).write_text(json.dumps(g, indent=1))
        return 0
    fmt = getattr(args, "format", None)
    if fmt:
        trials = None
        if fmt in ("json", "md", "html"):
            trials = [row for name, agent in ags.items() for row in reports.trial_rows(name, agent, runner.runs(agent), args.mode)]
        out = {"json": lambda: json.dumps(reports.to_versioned_json(res, args.mode, trials), indent=1),
               "junit": lambda: reports.to_junit(res, args.mode), "sarif": lambda: json.dumps(reports.to_sarif(res, args.mode), indent=1),
               "md": lambda: reports.to_markdown(res, args.mode, trials), "html": lambda: reports.to_html(res, args.mode, trials),
               "csv": lambda: "agent,id,status,detail\n" + "".join(f'{a},{i},{c["status"]},"{c["detail"].replace(chr(34), chr(39))}"\n' for a, row in res.items() for i, c in row.items())}[fmt]()
        if not args.out:  # report to stdout, so it can be piped
            print(out)
            return 1 if args.strict and any(c["status"] == "fail" for row in res.values() for c in row.values()) else 0
        Path(args.out).write_text(out)
    print(format_run_summary(res, args.mode))
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1))
    failed = any(c["status"] == "fail" for row in res.values() for c in row.values())
    return 1 if args.strict and failed else 0
