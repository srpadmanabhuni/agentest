"""``agentest`` command line: ``list``, ``run``, ``report``, ``version`` / ``--version`` and ``std`` (the standards-based engine).

No network calls by default: ``run --agent mock`` is fully in-process; only an http(s) ``--agent`` you give is contacted.
``--hub-catalogue`` (or AGENTEST_HUB_CATALOGUE=1) opts in to the pinned, sha256-checked, cached catalogue from the Hub."""

from __future__ import annotations

import argparse
import json
import os
import sys


def build_parser() -> argparse.ArgumentParser:
    from agentest import __version__

    parser = argparse.ArgumentParser(
        prog="agentest", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Agentic AI Test Checklist: 130 universal checks over OpenTelemetry GenAI traces",
        epilog="quickstart:\n  agentest list --packs\n  agentest run --agent mock --pack security\n  agentest report --format markdown\n"
               "  python -m agentest.mock_agent --port 8765   # then: agentest run --agent http://127.0.0.1:8765")
    parser.add_argument("--version", action="version", version=__version__, help="Print the agentest version and exit")
    sub = parser.add_subparsers(dest="cmd")
    hub = argparse.ArgumentParser(add_help=False)
    hub.add_argument("--hub-catalogue", action="store_true",
                     help="Read the catalogue from the published dataset (pinned revision, sha256-checked, fetched once "
                          "and cached; falls back to the vendored copy). Default: vendored copy, no network")

    lst = sub.add_parser("list", parents=[hub], help="List catalogue tests, optionally filtered by class (T1..T7)")
    lst.add_argument("--class", dest="class_id", default=None, help="Class ID, e.g. T3")
    lst.add_argument("--json", action="store_true", help="Emit JSON")
    lst.add_argument("--packs", action="store_true", help="List test packs (name and test count) instead of tests")
    lst.add_argument("--pack", default=None, help="Only the tests in this pack (see --packs)")

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
    sd.add_argument("action", choices=["validate", "run", "regress", "export", "gen", "catalog", "import", "serve"])
    sd.add_argument("inputs", nargs="*", help="import: native log files (.json / .jsonl)")
    sd.add_argument("--agent", default=None, help="Limit to one agent directory id")
    sd.add_argument("--ids", default=None, help="run: limit the report to these test IDs (comma-separated, e.g. T6-006,T2-008)")
    sd.add_argument("--agents", default=None, help="Directory of agent directories (default: agents/)")
    sd.add_argument("--mode", choices=["strict", "examples"], default="examples",
                    help="strict: only standard OTel/A2A/MCP fields; examples: also AgentCard skill examples")
    sd.add_argument("--json", default=None, help="run/regress: write JSON here")
    sd.add_argument("--out", default=None, help="run: report file; export/serve: output directory; import: output .otlp.jsonl")
    sd.add_argument("--strict", action="store_true", help="run: exit 1 on any fail")
    sd.add_argument("--format", choices=["json", "junit", "sarif", "md", "html", "csv"], default=None,
                    help="run/catalog: report format (json = versioned verdicts.schema.json)")
    sd.add_argument("--otlp", nargs="+", default=None, help="run: judge plain OTLP trace files (OTLP/JSON .json/.jsonl, OTLP/protobuf .pb)")
    sd.add_argument("--card", default=None, help="with --otlp: optional A2A AgentCard JSON")
    sd.add_argument("--tools", default=None, help="with --otlp / import: optional MCP tools/list JSON")
    sd.add_argument("--config", default=None, help="YAML/JSON config: disable IDs, thresholds, rules_dir, scenarios")
    sd.add_argument("--rules-dir", default=None, help="import extra @rule plugins from this directory")
    sd.add_argument("--emit-otlp", default=None, help="run: also write the verdicts as OTLP/JSON (gen_ai.evaluation.result events)")
    sd.add_argument("--dialect", default=None, help="import: native log dialect (steps, events, openai_agents, langgraph_msgs, autogen, n8n, file:my.py)")
    sd.add_argument("--map", default=None, help="import: mapping file (JSON): dialect, framework, observations, labels")
    sd.add_argument("--service", default=None, help="import: service / agent name written to the traces")
    sd.add_argument("--host", default="127.0.0.1", help="serve: bind address")
    sd.add_argument("--port", type=int, default=4318, help="serve: port (OTLP/HTTP default 4318)")
    sd.add_argument("--max-requests", type=int, default=0, help="serve: stop after N export requests (0 = run until interrupted)")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
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
    parser.print_help()
    return 2


def _cmd_list(args: argparse.Namespace) -> int:
    """Print catalogue rows (ID, class, title), optionally filtered by class."""
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
    rows = list(catalogue().values())
    if args.pack:
        ids = packs().get(args.pack.lower())
        if ids is None:
            print(f"unknown pack {args.pack!r}; see 'agentest list --packs'", file=sys.stderr)
            return 2
        cat = catalogue()
        from agentest.standards.catalog import what

        rows = [cat.get(i) or {"id": i, "class_id": "X", "title": what(i), "severity": None} for i in ids]
    if args.class_id:
        cid = args.class_id.upper()
        rows = [r for r in rows if r.get("class_id") == cid]
        if not rows:
            print(f"No tests for class {cid}; valid classes are T1..T7", file=sys.stderr)
            return 2
    if args.json:
        print(json.dumps([{k: r.get(k) for k in ("id", "class_id", "title", "severity")} for r in rows], indent=2))
    else:
        for r in rows:
            print(f"{r['id']}  [{r['class_id']}] {r['title']}")
        print(f"{len(rows)} test(s)")
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
        print(f"no results at {src}; run 'agentest run --agent mock' first", file=sys.stderr)
        return 2
    text = local.render(json.loads(src.read_text()), args.format)
    if args.out:
        Path(args.out).write_text(text)
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
