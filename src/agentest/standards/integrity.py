"""Pre-scoring trace integrity validator (r12-prep, Fix 7). Stdlib only.

Reads the per-agent export folders used in blind rounds and refuses, before any scoring, a folder whose evidence is
incomplete. It never runs a rule and never changes a verdict; it only says whether the exported evidence is complete
enough to be scored.

Export layout checked (one folder per agent; see docs/r12/TRACE_SCHEMA.md for the plain-words version)::

  agent-card.json         A2A AgentCard (governance extension optional)
  tools.json              MCP tools/list result; readOnlyHint=false marks a write tool
  traces/*.otlp.jsonl     OTLP/JSON, one export per line; spans of a traceId may be split over lines
  traffic/*.jsonl         harness-intercepted, HMAC-signed tool traffic: one record per real tool call
                          {trace_id, call_id, tool, args_sha256, result_sha256, hmac}

Per trace (one traceId = one run of one input):
  * resource attributes carry the harness signature (agentest.trace.chain / .hmac / .key_id / .alg)
  * one root span (no parent) with gen_ai.operation.name=invoke_agent, gen_ai.input.messages,
    gen_ai.output.messages and agentest.final_state
  * every tool call is an execute_tool span with gen_ai.tool.name, gen_ai.tool.call.id, gen_ai.tool.call.arguments and
    gen_ai.tool.call.result (or error.type)
  * observed effects of successful write calls are agentest.state_change span events

Exit status: 0 = every agent clean (warnings allowed), 1 = at least one ERROR, 2 = usage error.
Usage: python -m agentest.standards.integrity AGENTS_DIR [--trace-key-file F] [--json OUT] [--allow-unsigned]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agentest.standards import trust
from agentest.standards.metadata import load, trace_files
from agentest.standards.otel import split_traces

ROOT_REQUIRED = ("gen_ai.input.messages", "gen_ai.output.messages", "agentest.final_state")
TOOL_REQUIRED = ("gen_ai.tool.name", "gen_ai.tool.call.id", "gen_ai.tool.call.arguments")
TRAFFIC_REQUIRED = ("trace_id", "call_id", "tool", "args_sha256", "result_sha256", "hmac")
TRUNC_MARKERS = ("…[truncated]", "[truncated]", "...(truncated)", "<truncated>")
SIZE_CAPS = (1024, 2048, 4096, 8192, 16384, 32768, 65536)  # a string exactly this long is probably cut by an exporter


def _attr(s: dict, k: str):
    return trust._attr(s, k)


def _read_lines(f: Path, errs: list[str]) -> list[dict]:
    if f.suffix in (".pb", ".binpb"):
        from agentest.standards.otel import read_otlp_file

        return read_otlp_file(f)
    text = f.read_text(encoding="utf-8", errors="replace")
    if f.suffix == ".json":
        try:
            return [json.loads(text)]
        except ValueError as e:
            errs.append(f"{f.name}: not valid JSON ({e.msg} at char {e.pos}): truncated or corrupt export")
            return []
    out = []
    lines = text.splitlines()
    for i, ln in enumerate(lines, 1):
        if not ln.strip():
            continue
        try:
            out.append(json.loads(ln))
        except ValueError as e:
            errs.append(f"{f.name}:{i}: not valid JSON ({e.msg}): truncated or corrupt line")
    if text and not text.endswith("\n") and lines and out and lines[-1].strip() and not _ok_json(lines[-1]):
        errs.append(f"{f.name}: last line has no newline and does not parse: export cut off")
    return out


def _ok_json(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except ValueError:
        return False


def check_trace(doc: dict, agent, traffic: list[dict] | None, key: bytes | None, allow_unsigned: bool, allow_no_traffic: bool = False) -> tuple[list[str], list[str], dict]:
    """(errors, warnings, stats) for one trace document."""
    E, W = [], []
    spans = trust._spans(doc)
    ids = {s.get("spanId") for s in spans}
    tid = next((s.get("traceId") for s in spans), "?")
    roots = [s for s in spans if not s.get("parentSpanId")]
    op = lambda s: _attr(s, "gen_ai.operation.name")  # noqa: E731
    if not spans:
        return [f"trace {tid}: no spans"], W, {}
    # --- signature
    st, why = trust.verify(doc, key)
    if st == "unsigned" and not allow_unsigned:
        E.append(f"trace {tid}: unsigned ({why})")
    elif st == "bad-signature":
        E.append(f"trace {tid}: bad signature ({why})")
    elif st == "no-key":
        W.append(f"trace {tid}: signed but not verified (no harness key given)")
    # --- completeness / truncation
    if not any(op(s) == "invoke_agent" for s in roots):
        E.append(f"trace {tid}: no root invoke_agent span (run not exported or cut off)")
    for r in (s for s in roots if op(s) == "invoke_agent"):
        miss = [k for k in ROOT_REQUIRED if _attr(r, k) in (None, "")]
        if miss:
            E.append(f"trace {tid}: root span lacks {miss} (run incomplete)")
    orphans = [s.get("spanId") for s in spans if s.get("parentSpanId") and s.get("parentSpanId") not in ids]
    if orphans:
        E.append(f"trace {tid}: {len(orphans)} span(s) whose parent is missing (spans dropped / export truncated)")
    for s in spans:
        try:
            a, b = int(s.get("startTimeUnixNano") or 0), int(s.get("endTimeUnixNano") or 0)
        except (TypeError, ValueError):
            a, b = 0, 0
        if not b or b < a:
            E.append(f"trace {tid}: span {s.get('name')!r} has no valid end time (unfinished span)")
            break
    for s in spans:
        for at in s.get("attributes", []):
            v = (at.get("value") or {}).get("stringValue")
            if isinstance(v, str) and (v.rstrip().endswith(TRUNC_MARKERS) or len(v) in SIZE_CAPS):
                W.append(f"trace {tid}: {s.get('name')}.{at.get('key')} looks truncated (len {len(v)})")
    # --- tool calls
    tools = [s for s in spans if op(s) == "execute_tool"]
    if not tools and trust.has_message_only_calls(doc):
        E.append(f"trace {tid}: tool calls exist only in model messages (no execute_tool spans)")
    for s in tools:
        miss = [k for k in TOOL_REQUIRED if _attr(s, k) in (None, "")]
        if _attr(s, "gen_ai.tool.call.result") is None and not _attr(s, "error.type"):
            miss.append("gen_ai.tool.call.result|error.type")
        if miss:
            E.append(f"trace {tid}: execute_tool span {_attr(s, 'gen_ai.tool.name') or '?'} lacks {miss}")
    # --- signed tool traffic
    if traffic is None:
        if tools:
            (W if allow_no_traffic else E).append(f"trace {tid}: {len(tools)} tool call(s) but no intercepted tool traffic (traffic/*.jsonl missing)")
    elif key is not None:
        xc = trust.cross_check(doc, traffic, key)
        if xc:
            E.append(f"trace {tid}: traffic cross-check: {len(xc)} problem(s), e.g. {xc[0]}")
    else:
        recs = {r.get("call_id") for r in traffic if r.get("trace_id") == tid}
        spans_c = {str(_attr(s, "gen_ai.tool.call.id") or "") for s in tools}
        if spans_c - recs:
            E.append(f"trace {tid}: {len(spans_c - recs)} execute_tool span(s) with no traffic record")
        if recs - spans_c:
            E.append(f"trace {tid}: {len(recs - spans_c)} traffic record(s) with no execute_tool span")
    # --- state transitions
    ok_writes = [s for s in tools if agent.is_write(str(_attr(s, "gen_ai.tool.name") or "")) and not _attr(s, "error.type")]
    changes = [e for s in spans for e in s.get("events", []) if e.get("name") == "agentest.state_change"]
    if ok_writes and not changes:
        # legitimate for an idempotent re-run ("already processed"); an ERROR only when no trace of the agent has any
        W.append(f"trace {tid}: {len(ok_writes)} successful write call(s) but no agentest.state_change events")
    return E, W, {"spans": len(spans), "tool_calls": len(tools), "writes_ok": len(ok_writes), "state_changes": len(changes)}


def check_agent(adir: Path, key: bytes | None, allow_unsigned: bool = False, allow_no_traffic: bool = False) -> dict:
    E, W = [], []
    a = load(adir)
    if not (adir / "tools.json").exists():
        W.append("tools.json missing: every tool is treated as a write (MCP default)")
    if not (adir / "agent-card.json").exists():
        W.append("agent-card.json missing")
    files = trace_files(a)
    if not files:
        return {"agent": adir.name, "status": "ERROR", "errors": ["no trace files"], "warnings": W, "traces": 0}
    raw = [d for f in files for d in _read_lines(f, E)]
    docs = split_traces({"resourceSpans": [rs for d in raw for rs in d.get("resourceSpans", [])]}) if raw else []
    tf = trust.traffic_files(adir)
    traffic = None
    if tf:
        traffic = []
        for f in tf:
            for i, r in enumerate(_read_lines(f, E), 1):
                miss = [k for k in TRAFFIC_REQUIRED if not r.get(k)]
                if miss:
                    E.append(f"{f.name}:{i}: traffic record lacks {miss}")
                traffic.append(r)
    stats = {"traces": len(docs), "spans": 0, "tool_calls": 0, "writes_ok": 0, "state_changes": 0,
             "traffic_records": None if traffic is None else len(traffic)}
    for d in docs:
        e, w, s = check_trace(d, a, traffic, key, allow_unsigned, allow_no_traffic)
        E += e
        W += w
        for k, v in s.items():
            stats[k] += v
    if stats["writes_ok"] and not stats["state_changes"]:
        E.append(f"{stats['writes_ok']} successful write call(s) over {len(docs)} trace(s) but no agentest.state_change "
                 "event at all: state transitions were not exported")
    if a.tools and docs and stats["tool_calls"] == 0:
        E.append(f"{len(a.tools)} tool(s) declared but no execute_tool span in any trace")
    return {"agent": adir.name, "status": "ERROR" if E else ("WARN" if W else "OK"), "errors": E, "warnings": W, **stats}


def agent_dirs(p: Path) -> list[Path]:
    if (p / "traces").is_dir() or (p / "agent-card.json").exists():
        return [p]
    return sorted(x for x in p.iterdir() if x.is_dir() and ((x / "traces").is_dir() or (x / "agent-card.json").exists()))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="agentest-integrity", description=__doc__.split("\n\n")[0])
    ap.add_argument("path", type=Path, help="an agent export folder, or a folder of them")
    ap.add_argument("--trace-key-file", help="harness key: verify trace signatures and traffic HMACs")
    ap.add_argument("--allow-unsigned", action="store_true", help="dev traces: an unsigned trace is not an error")
    ap.add_argument("--dev", action="store_true", help="dev / pre-v4.0-trust exports: unsigned traces and missing traffic are warnings")
    ap.add_argument("--json", type=Path, help="write the full report as JSON")
    ap.add_argument("--max-lines", type=int, default=3, help="problems printed per agent (all go to --json)")
    a = ap.parse_args(argv)
    if not a.path.is_dir():
        print(f"not a folder: {a.path}", file=sys.stderr)
        return 2
    key = trust.load_key(a.trace_key_file) if a.trace_key_file else None
    rep = [check_agent(d, key, a.allow_unsigned or a.dev, a.dev) for d in agent_dirs(a.path)]
    for r in rep:
        print(f"{r['agent']}: {r['status']}  traces={r['traces']} tool_calls={r.get('tool_calls', 0)} "
              f"traffic={r.get('traffic_records')} state_changes={r.get('state_changes', 0)} "
              f"errors={len(r['errors'])} warnings={len(r['warnings'])}")
        for x in r["errors"][: a.max_lines]:
            print(f"  ERROR {x}")
        for x in r["warnings"][: max(0, a.max_lines - len(r['errors']))]:
            print(f"  warn  {x}")
    bad = [r["agent"] for r in rep if r["status"] == "ERROR"]
    print(f"integrity: {len(rep) - len(bad)}/{len(rep)} agent(s) scoreable" + (f"; REFUSE: {', '.join(bad)}" if bad else ""))
    if a.json:
        a.json.write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
