"""``agentest`` command line: ``list``, ``run``, ``report``, ``version`` / ``--version``, ``std`` and ``demo``.

No network calls by default: ``run --agent mock`` is fully in-process; only an http(s) ``--agent`` you give is contacted.
``--hub-catalogue`` (or AGENTEST_HUB_CATALOGUE=1) opts in to the pinned, sha256-checked, cached catalogue from the Hub."""
# Ref: internal design (docs/USER-GUIDE.md, docs/HOW-IT-WORKS.md); the std subcommands are in src/agentest/standards/cli.py.

from __future__ import annotations

import argparse
import json
import os
import sys


def build_parser() -> argparse.ArgumentParser:
    from agentest import __version__

    parser = argparse.ArgumentParser(
        prog="agentest", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Agentic AI Test Checklist: 165 tests over OpenTelemetry GenAI traces",
        epilog="quickstart:\n  pip install agentest-ai\n  agentest demo\n"
               "  # offline, no trace file of your own; prints pass/fail/n/a counts and a few findings\n"
               "  # write an HTML report with: agentest demo --html\n"
               "  agentest std run --agent a22 --ids T1-018 --format md\n"
               "  # expected: T1-018 | fail | case2#0: claims success\n"
               "  # with no --agent and no --otlp, std run judges every bundled agent\n"
               "  agentest std diff old.json new.json\n"
               "  # transitions between two saved `agentest std run --json` files, grouped by task and check\n"
               "  # --fail-on-new-fail exits 1 when a check newly fails")
    parser.add_argument("--version", action="version", version=__version__, help="Print the agentest version and exit")
    sub = parser.add_subparsers(dest="cmd")
    hub = argparse.ArgumentParser(add_help=False)
    hub.add_argument("--hub-catalogue", action="store_true",
                     help="Read the catalogue from the published dataset (pinned revision, sha256-checked, fetched once "
                          "and cached; falls back to the vendored copy). Default: vendored copy, no network")

    lst = sub.add_parser("list", parents=[hub], help="List catalogue tests, optionally filtered by class (T1..T7 or X), severity or eval group")
    lst.add_argument("--class", dest="class_id", default=None, help="Class ID: T1..T7 or X (repo extensions)")
    lst.add_argument("--severity", default=None, help="Comma-separated severities, e.g. critical,high (default: all)")
    lst.add_argument("--group", default=None, help="Comma-separated eval groups, e.g. security,privacy (default: all)")
    lst.add_argument("--json", action="store_true", help="Emit JSON")
    lst.add_argument("--packs", action="store_true", help="List test packs (name and test count) instead of tests")
    lst.add_argument("--pack", default=None, help="Only the tests in this pack (see --packs)")
    lst.add_argument("--opt-in", action="store_true", dest="opt_in",
                     help="List the five opt-in responsible-AI additions")
    lst.add_argument("--new-tests", action="store_true", dest="new_tests",
                     help="List the opt-in New tests and, when present, T1-020 and T1-021")

    rn = sub.add_parser("run", parents=[hub], help="Probe an agent (mock or http endpoint), judge its traces, save results")
    rn.add_argument("--agent", required=True, help="'mock' (built-in, offline) or an http(s):// endpoint (see agentest.mock_agent for the contract)")
    rn.add_argument("--pack", default="all", help="Test pack to report (default: all; see 'agentest list --packs')")
    rn.add_argument("--mode", choices=["strict", "examples"], default="examples", help="strict: only standard OTel/A2A/MCP fields")
    rn.add_argument("--out", default=None, help="Where to save results (default: .agentest/last-run.json)")
    rn.add_argument("--timeout", type=float, default=60, help="Per-request timeout in seconds for http endpoints")
    rn.add_argument("--strict", action="store_true", help="Exit 1 if any check fails")

    rp = sub.add_parser("report", help="Render saved results from 'agentest run' as markdown or JSON")
    rp.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Report format (default: markdown)")
    rp.add_argument("--input", default=None, help="Results file (default: .agentest/last-run.json)")
    rp.add_argument("--out", default=None, help="Write the report here instead of stdout")

    sub.add_parser("version", help="Print the agentest version")

    sd = sub.add_parser("std", parents=[hub], help="Standards-based checks: OTel GenAI traces + A2A AgentCard + MCP tool annotations")
    sd.add_argument("action", choices=["validate", "run", "regress", "export", "gen", "catalog", "import", "serve", "diff", "postconditions"],
                    help="diff: compare two saved `agentest std run --json` files (OLD.json NEW.json)")
    sd.add_argument("inputs", nargs="*", help="import: native log files (.json / .jsonl); diff: OLD.json NEW.json")
    sd.add_argument("--agent", default=None, help="Limit to one agent directory id")
    sd.add_argument("--ids", default=None,
                     help=("run: limit the report to test IDs or classes T1-T7, X (comma-separated, e.g. T5,T6-002); "
                           "also accepts NT (opt-in New tests, plus T1-020 and T1-021) and "
                           "the five opt-in responsible-AI additions (agentest list --opt-in)"))
    sd.add_argument("--pack", default=None, help="run: only the checks of these packs (comma-separated; see 'agentest list --packs', e.g. ma,pv or rai); packs are opt-in and never in the default run")
    sd.add_argument("--agents", default=None, help="Directory of agent directories (default: agents/)")
    sd.add_argument("--mode", choices=["strict", "examples"], default="examples",
                    help="strict: only standard OTel/A2A/MCP fields; examples: also AgentCard skill examples")
    sd.add_argument("--json", default=None, help="run/regress/diff/postconditions: write JSON here")
    sd.add_argument("--out", default=None, help="run: report file; export/serve: output directory; import: output .otlp.jsonl")
    sd.add_argument("--strict", action="store_true", help="run: exit 1 on any fail; postconditions: exit 1 on any unmet end state")
    sd.add_argument("--fail-on-new-fail", action="store_true",
                    help="diff: exit 1 when a check newly fails (its status becomes fail)")
    sd.add_argument("--format", choices=["json", "junit", "sarif", "md", "html", "csv"], default=None,
                    help="run/catalog: report format (json = versioned verdicts.schema.json)")
    sd.add_argument("--otlp", nargs="+", default=None, help="run: judge plain OTLP trace files (OTLP/JSON .json/.jsonl, OTLP/protobuf .pb)")
    sd.add_argument("--card", default=None, help="with --otlp: optional A2A AgentCard JSON")
    sd.add_argument("--tools", default=None, help="with --otlp / import: optional MCP tools/list JSON")
    sd.add_argument("--config", default=None, help="YAML/JSON config: disable IDs, thresholds, rules_dir, scenarios")
    sd.add_argument("--rules-dir", default=None, help="import extra @rule plugins from this directory")
    sd.add_argument("--emit-otlp", default=None, help="run: also write the verdicts as OTLP/JSON (gen_ai.evaluation.result events)")
    sd.add_argument("--dialect", default=None, help="import: native log dialect (steps, events, openai_agents, langgraph_msgs, autogen, smolagents, n8n, file:my.py)")
    sd.add_argument("--map", default=None, help="import: mapping file (JSON): dialect, framework, observations, labels")
    sd.add_argument("--service", default=None, help="import: service / agent name written to the traces")
    sd.add_argument("--trace-format", action="store_true", help="import: also write the run-level trace format 1.0.0 attributes to the resource")
    sd.add_argument("--host", default="127.0.0.1", help="serve: bind address")
    sd.add_argument("--port", type=int, default=4318, help="serve: port (OTLP/HTTP default 4318)")
    sd.add_argument("--max-requests", type=int, default=0, help="serve: stop after N export requests (0 = run until interrupted)")

    dm = sub.add_parser(
        "demo",
        help="Run a bundled sample trace and print a short pass/fail/n/a summary (offline, no files needed)",
    )
    dm.add_argument("--agent", default="overreach", help="Bundled sample agent to judge (default: overreach)")
    dm.add_argument(
        "--html", nargs="?", const="agentest-demo-report.html", default=None, metavar="PATH",
        help="Also write an HTML report (default path: agentest-demo-report.html)",
    )
    dm.add_argument("--no-color", action="store_true", help="Disable ANSI colours")

    return parser


CLONE_HINT = (
    "Paths such as examples/... ship with the source repository, not with pip install agentest-ai.\n"
    "  To use them, clone it first:\n"
    "    git clone --depth 1 https://github.com/srpadmanabhuni/agentest.git && cd agentest\n"
    "  Or try what ships with the package:\n"
    "    agentest demo\n"
    "    agentest std run --agent a22 --ids T1-018 --format md"
)


def missing_path_message(path: object) -> str:
    """The friendly message for a path that does not exist (exit code 2, like other bad input)."""
    return f"agentest: {path} not found.\n{CLONE_HINT}"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _dispatch(parser, args)
    except FileNotFoundError as e:
        print(missing_path_message(e.filename or e), file=sys.stderr)
        return 2


def _dispatch(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    if getattr(args, "hub_catalogue", False):
        os.environ["AGENTEST_HUB_CATALOGUE"] = "1"
    if args.cmd == "std":
        from agentest.standards.cli import cmd_std

        return cmd_std(args)
    if args.cmd == "version":
        from agentest import __version__

        print(__version__)
        return 0
    if args.cmd == "list":
        return _cmd_list(args)
    if args.cmd == "run":
        return _cmd_run(args)
    if args.cmd == "report":
        return _cmd_report(args)
    if args.cmd == "demo":
        return _cmd_demo(args)
    parser.print_help()
    return 2


def _parse_multi(value: str | None) -> list[str]:
    """Split a comma-separated CLI value into normalised, non-empty tokens."""
    if not value:
        return []
    return [part.strip().lower() for part in value.split(",") if part.strip()]


def _filter_field(rows: list[dict], cat_rows: list[dict], field: str, wanted: list[str], label: str) -> list[dict] | None:
    """Keep rows whose ``field`` is in ``wanted``; None (after printing the valid set) if a value is unknown."""
    known = sorted({str(r.get(field)).lower() for r in cat_rows if r.get(field)})
    unknown = [w for w in wanted if w not in known]
    if unknown:
        print(f"No tests for {label} {','.join(unknown)}; valid {label}s are {','.join(known)}", file=sys.stderr)
        return None
    return [r for r in rows if str(r.get(field) or "").lower() in wanted]


def _cmd_list(args: argparse.Namespace) -> int:
    """Print catalogue rows (ID, class, title), optionally filtered by class, severity or eval group."""
    from agentest.local import packs
    from agentest.standards.catalog import catalogue

    if args.packs:
        pk = packs()
        if args.json:
            print(json.dumps({k: len(v) for k, v in pk.items()}, indent=2))
        else:
            for k, v in pk.items():
                print(f"{k:24} {len(v)} test(s)")
        return 0
    if getattr(args, "opt_in", False) and not args.packs:
        return _cmd_list_opt_in(args)
    if getattr(args, "new_tests", False) and not args.packs:
        return _cmd_list_new_tests(args)
    rows = list(catalogue().values())
    if args.pack:
        ids = packs().get(args.pack.lower())
        if ids is None:
            print(f"unknown pack {args.pack!r}; see 'agentest list --packs'", file=sys.stderr)
            return 2
        cat = catalogue()
        from agentest.standards.catalog import what
        from agentest.standards.packs import rows as pack_rows

        prow = pack_rows()
        rows = [cat.get(i) or ({"id": i, "class_id": i[:2], "title": prow[i]["title"], "severity": prow[i]["severity"], "eval_group": prow[i]["family"]} if i in prow
                               else {"id": i, "class_id": "X", "title": what(i), "severity": None}) for i in ids]
    if args.class_id:
        cid = args.class_id.upper()
        if cid == "X" and not args.pack:
            from agentest.standards.catalog import what
            from agentest.standards.rules import RULES

            rows = [{"id": i, "class_id": "X", "title": what(i), "severity": None}
                    for i in sorted(RULES) if i.startswith("X-")]
        rows = [r for r in rows if r.get("class_id") == cid]
        if not rows:
            print(f"No tests for class {cid}; valid classes are T1..T7 and X", file=sys.stderr)
            return 2
    full = list(catalogue().values())
    for field, label, raw in (("severity", "severity", args.severity), ("eval_group", "group", args.group)):
        wanted = _parse_multi(raw)
        if wanted:
            rows = _filter_field(rows, full, field, wanted, label)
            if rows is None:
                return 2
    if args.json:
        print(json.dumps([{**{k: r.get(k) for k in ("id", "class_id", "title", "severity")}, "eval_group": r.get("eval_group")} for r in rows], indent=2))
    else:
        for r in rows:
            print(f"{r['id']}  [{r['class_id']}] {r['title']}")
        print(f"{len(rows)} test(s)")
    return 0



def _cmd_list_new_tests(args: argparse.Namespace) -> int:
    """List the opt-in New tests (NT-xxx) and, when present, T1-020 and T1-021."""
    from agentest.standards.catalog import new_tests, rai_additions

    rows = list(new_tests().values())
    shipped: list[dict] = []
    try:
        from agentest.standards.new_tests.b3 import PHASE1_SHIPPED, PHASE1_SHIPPED_CLOSES
        rai = rai_additions()
        for i in PHASE1_SHIPPED:
            src = rai.get(i, {"id": i, "title": i, "class_id": i.split("-")[0]})
            closes = PHASE1_SHIPPED_CLOSES.get(i, ())
            shipped.append({
                "id": i,
                "class_id": src.get("class_id", i.split("-")[0]),
                "title": src.get("title", i),
                "article_test": closes[0] if closes else src.get("article_test", ""),
                "opt_in": True,
                "phase1_shipped": True,
            })
    except ImportError:
        pass
    listed = [{k: r.get(k) for k in ("id", "class_id", "title", "article_test")} | {"opt_in": True} for r in rows] + shipped
    if args.json:
        print(json.dumps(listed, indent=2))
    else:
        for r in listed:
            print(f"{r['id']}  [{r.get('article_test', '')}] {r['title']}  [opt-in]")
        if shipped:
            print(f"{len(rows)} New test(s) and {len(shipped)} shipped design(s) (opt-in)")
        else:
            print(f"{len(rows)} New test(s) (opt-in)")
    return 0


def _cmd_list_opt_in(args: argparse.Namespace) -> int:
    """List the five responsible-AI additions, marked as opt-in."""
    from agentest.standards.catalog import catalogue, rai_additions

    rows = list(rai_additions().values())
    if args.pack:
        print("agentest list --opt-in does not use --pack; drop --pack or drop --opt-in", file=sys.stderr)
        return 2
    if args.class_id:
        cid = args.class_id.upper()
        rows = [r for r in rows if r.get("class_id") == cid]
        if not rows:
            print(f"No opt-in tests for class {cid}; valid classes are T1..T7 and X", file=sys.stderr)
            return 2
    full = list(catalogue().values()) + list(rai_additions().values())
    for field, label, raw in (("severity", "severity", args.severity), ("eval_group", "group", args.group)):
        wanted = _parse_multi(raw)
        if wanted:
            rows = _filter_field(rows, full, field, wanted, label)
            if rows is None:
                return 2
    if args.json:
        print(json.dumps([{**{k: r.get(k) for k in ("id", "class_id", "title", "severity")},
                           "eval_group": r.get("eval_group"), "opt_in": True} for r in rows], indent=2))
    else:
        for r in rows:
            print(f"{r['id']}  [{r['class_id']}] {r['title']}  [opt-in]")
        print(f"{len(rows)} opt-in test(s)")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    from pathlib import Path

    from agentest import local

    try:
        saved = local.run(args.agent, args.pack, args.mode, args.timeout)
    except KeyError:
        print(f"unknown pack {args.pack!r}; see 'agentest list --packs'", file=sys.stderr)
        return 2
    except Exception as e:  # endpoint errors, bad URLs, empty traces
        print(f"run failed: {e}", file=sys.stderr)
        return 2
    out = Path(args.out) if args.out else local.DEFAULT_RESULTS
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(saved, indent=1))
    res = saved["results"]
    tot = {s: sum(c["status"] == s for row in res.values() for c in row.values()) for s in ("pass", "fail", "n/a")}
    print(f"pack {saved['pack']}: {tot['pass']} pass, {tot['fail']} fail, {tot['n/a']} n/a; saved to {out}")
    print("next: agentest report --format markdown" + (f" --input {out}" if args.out else ""))
    return 1 if args.strict and tot["fail"] else 0


def _cmd_report(args: argparse.Namespace) -> int:
    from pathlib import Path

    from agentest import local

    src = Path(args.input) if args.input else local.DEFAULT_RESULTS
    if not src.exists():
        print(f"no results at {src}; this command reads a saved probe run. For the standards first-run use: "
              f"agentest std run --agent a22 --ids T1-018 --format md. To use this report command, first run "
              f"agentest run --agent mock.", file=sys.stderr)
        return 2
    text = local.render(json.loads(src.read_text(encoding="utf-8")), args.format)
    if args.out:
        Path(args.out).write_text(text)
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


# Findings shown first in `agentest demo` when they fail; then any other fails, by ID.
_DEMO_FINDINGS = (
    "T5-007",  # write without confirm
    "T3-007",  # privileged tool after role downgrade
    "T2-004",  # disbursement without approval
    "T3-011",  # delete with ambient authority
    "T5-001",  # off-list tool
    "T5-008",  # path escape
    "T4-001",  # followed a hidden instruction
    "T3-001",  # privileged action without a grant
)


def _color_enabled(no_color: bool) -> bool:
    if no_color or os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR") or os.environ.get("CLICOLOR_FORCE"):
        return True
    return sys.stdout.isatty()


def _paint(text: str, code: str, on: bool) -> str:
    return f"\033[{code}m{text}\033[0m" if on else text


def _finding_title(test_id: str) -> str:
    from agentest.standards.catalog import X_WHAT, catalogue

    title = (catalogue().get(test_id) or {}).get("title") or ""
    if title:
        return title
    return X_WHAT.get(test_id, "")


def _example_findings(row: dict, n: int = 5) -> list[tuple[str, dict]]:
    fails = {i: c for i, c in row.items() if c["status"] == "fail"}
    picked: list[tuple[str, dict]] = []
    seen: set[str] = set()
    for i in _DEMO_FINDINGS:
        if i in fails:
            picked.append((i, fails[i]))
            seen.add(i)
        if len(picked) >= n:
            return picked
    for i, c in sorted(fails.items()):
        if i not in seen:
            picked.append((i, c))
        if len(picked) >= n:
            break
    return picked


def format_demo_report(
    res: dict,
    *,
    version: str,
    agent: str,
    color: bool,
    html_path: str | None = None,
    n_findings: int = 5,
) -> str:
    """Short coloured summary of a demo run: counts plus a few example findings."""
    row = res.get(agent) or (next(iter(res.values())) if res else {})
    tot = {s: sum(c["status"] == s for c in row.values()) for s in ("pass", "fail", "n/a")}
    findings = _example_findings(row, n_findings)
    bold, dim, green, red, yellow = "1", "2", "32", "31", "33"

    def p(text: str, code: str) -> str:
        return _paint(text, code, color)

    lines = [
        f"{p('agentest ' + version, bold)}  ·  bundled sample {p(agent, '36')}",
        "",
        "  "
        + p(f"{tot['pass']} passed", green)
        + "    "
        + p(f"{tot['fail']} failed", red)
        + "    "
        + p(f"{tot['n/a']} n/a", yellow),
        "",
    ]
    if findings:
        more = tot["fail"] - len(findings)
        head = f"  Example findings ({len(findings)} of {tot['fail']} failed):" if more > 0 else "  Example findings:"
        lines.append(p(head, dim) if more > 0 else head)
        for test_id, cell in findings:
            title = _finding_title(test_id)
            detail = cell.get("detail") or ""
            if len(detail) > 120:
                detail = detail[:117] + "..."
            lines.append(f"    {p('FAIL', red + ';1')}  {p(test_id, bold)}" + (f"  {title}" if title else ""))
            if detail:
                lines.append(f"          {p(detail, dim)}")
        lines.append("")
    elif tot["fail"] == 0:
        lines.append("  No failures on this sample.")
        lines.append("")

    lines.append("  Next:")
    if html_path:
        lines.append(f"    wrote HTML report to {html_path}")
    else:
        lines.append("    agentest demo --html report.html")
    lines.append("    agentest std run --otlp examples/first_trace/trace.otlp.json --tools examples/first_trace/tools.json --format md")
    return "\n".join(lines) + "\n"


def _cmd_demo(args: argparse.Namespace) -> int:
    """Judge one bundled sample agent and print a short pass/fail/n/a summary."""
    from pathlib import Path

    from agentest import __version__
    from agentest.standards import metadata, runner

    agent = args.agent
    try:
        ags = metadata.load_all()
    except Exception as e:
        print(f"demo: could not load bundled samples: {e}", file=sys.stderr)
        return 2
    if agent not in ags:
        known = ", ".join(sorted(ags))
        print(f"unknown agent {agent!r}; bundled samples include: {known}", file=sys.stderr)
        return 2
    res = runner.to_json(runner.run_all({agent: ags[agent]}, mode="examples"))
    html_path = None
    if args.html:
        dest = Path(args.html)
        dest.write_text(_demo_html(res, "examples", agent, __version__), encoding="utf-8")
        html_path = str(dest)
    text = format_demo_report(
        res, version=__version__, agent=agent,
        color=_color_enabled(args.no_color), html_path=html_path,
    )
    print(text, end="")
    return 0


def _demo_html(res: dict, mode: str, agent: str, version: str) -> str:
    import html as html_lib

    from agentest.standards import reports

    tot = {s: sum(c["status"] == s for row in res.values() for c in row.values()) for s in ("pass", "fail", "n/a")}
    banner = (
        f"<p><strong>{tot['pass']} passed</strong> · "
        f"<strong>{tot['fail']} failed</strong> · {tot['n/a']} n/a "
        f"on bundled sample {html_lib.escape(agent)}</p>"
    )
    return reports.to_html(res, mode).replace("<h1>", banner + "<h1>", 1)


if __name__ == "__main__":
    raise SystemExit(main())
