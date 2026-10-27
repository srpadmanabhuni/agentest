"""``agentest`` command line: ``list``, ``version`` and ``std`` (the standards-based engine)."""

from __future__ import annotations

import argparse
import json
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentest", description="Agentic AI Test Checklist: 130 universal checks over OpenTelemetry GenAI traces")
    sub = parser.add_subparsers(dest="cmd")

    lst = sub.add_parser("list", help="List catalogue tests, optionally filtered by class (T1..T7)")
    lst.add_argument("--class", dest="class_id", default=None, help="Class ID, e.g. T3")
    lst.add_argument("--json", action="store_true", help="Emit JSON")

    sub.add_parser("version", help="Print the agentest version")

    sd = sub.add_parser("std", help="Standards-based checks: OTel GenAI traces + A2A AgentCard + MCP tool annotations")
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
    sd.add_argument("--judge", default=None,
                    help="run/regress: OpenAI-compatible endpoint for semantic checks (e.g. http://127.0.0.1:8080/v1, 'local' = that URL, "
                         "'off'); default $AGENTEST_JUDGE_URL. Without a judge, semantic checks report not-assessed")
    sd.add_argument("--judge-model", default=None, help="judge model name (default $AGENTEST_JUDGE_MODEL or the local Qwen2.5-7B GGUF)")
    sd.add_argument("--judge-cache", default=None, help="judge answer cache (JSONL; default ~/.cache/agentest/judge.jsonl)")
    sd.add_argument("--judge-offline", action="store_true", help="replay cached judge answers only; never call an endpoint")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "std":
        from agentest.standards.cli import cmd_std

        return cmd_std(args)
    if args.cmd == "version":
        from agentest import __version__

        print(__version__)
        return 0
    if args.cmd == "list":
        return _cmd_list(args)
    parser.print_help()
    return 2


def _cmd_list(args: argparse.Namespace) -> int:
    """Print catalogue rows (ID, class, title), optionally filtered by class."""
    from agentest.standards.catalog import catalogue

    rows = list(catalogue().values())
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


if __name__ == "__main__":
    raise SystemExit(main())
