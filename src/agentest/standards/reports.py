"""Open output formats for verdicts: versioned JSON, JUnit XML, SARIF 2.1.0, Markdown and HTML.

All writers take the plain verdict mapping ``{agent: {id: {"status", "detail"}}}`` produced by
``runner.to_json`` and use only the standard library.
"""

from __future__ import annotations

import csv
import html
import io
import json
from xml.etree import ElementTree as ET

from agentest.standards import VERSION

VERDICTS_SCHEMA = "https://github.com/srpadmanabhuni/agentest/blob/main/src/agentest/standards/schemas/verdicts.schema.json"
SCHEMA_ID = "agentest.verdicts/1"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"


def _catalog() -> dict[str, dict]:
    from agentest.paths import root

    out = {}
    p = root() / "catalog" / "checklist-110.jsonl"
    if p.exists():
        for ln in p.read_text().splitlines():
            if ln.strip():
                d = json.loads(ln)
                out[d["id"]] = d
    return out


def _what(tid: str) -> str:
    from agentest.standards.rules import RULES

    return RULES[tid][0] if tid in RULES else ""


def _coverage(res: dict, coverage: dict | None) -> dict:
    from agentest.standards import instrumentation

    return coverage if coverage is not None else instrumentation.gate(res)


def to_versioned_json(res: dict, mode: str, coverage: dict | None = None) -> dict:
    from agentest.standards import judge

    return {"schema": SCHEMA_ID, "$schema": VERDICTS_SCHEMA, "tool": {"name": "agentest", "version": VERSION}, "mode": mode,
            "judge": judge.describe(), "coverage": _coverage(res, coverage),
            "results": [{"agent": a, "id": i, "status": c["status"], "detail": c["detail"], **({"judge": c["judge"]} if c.get("judge") else {}),
                         **({"severity": c["severity"]} if c.get("severity") else {}), **({"guide": c["guide"]} if c.get("guide") else {})}
                        for a, row in res.items() for i, c in row.items()]}


def _g(c: dict) -> str:
    from agentest.standards import guidance

    return (" | " + guidance.text(c["guide"])) if c.get("guide") else ""


def to_csv(res: dict) -> str:
    """CSV: agent,id,status,detail (+ guide when the cells carry guidance)."""
    q = lambda v: '"' + str(v).replace('"', "'") + '"'  # noqa: E731
    from agentest.standards import guidance

    has = any(c.get("guide") for row in res.values() for c in row.values())
    head = "agent,id,status,detail" + (",guide" if has else "") + "\n"
    return head + "".join(f'{a},{i},{c["status"]},{q(c["detail"])}' + (f',{q(guidance.text(c["guide"]) if c.get("guide") else "")}' if has else "") + "\n"
                          for a, row in res.items() for i, c in row.items())


def to_junit(res: dict, mode: str = "examples", coverage: dict | None = None) -> str:
    """JUnit XML: one <testsuite> per agent, one <testcase> per ID. fail -> <failure>; n/a, not-assessed, not-run -> <skipped>.
    Every suite carries the instrumentation coverage as <properties>; an agent above the n/a threshold gets one more
    <testcase name="agentest/instrumentation-coverage"> with a <failure>, so a JUnit consumer fails the build."""
    from agentest.standards import instrumentation

    cov = _coverage(res, coverage)
    suites = ET.Element("testsuites", name=f"agentest {VERSION} ({mode})")
    for a, row in res.items():
        ac = cov["agents"].get(a)
        gate_fail = bool(ac) and not ac["ok"]
        f = sum(c["status"] == "fail" for c in row.values()) + gate_fail
        sk = sum(c["status"] not in ("pass", "fail") for c in row.values())
        s = ET.SubElement(suites, "testsuite", name=a, tests=str(len(row) + gate_fail), failures=str(f), errors="0", skipped=str(sk))
        if ac:
            props = ET.SubElement(s, "properties")
            for k in ("na_share", "max_na_share", "considered", "n/a", "not-run", "not-assessed", "ok"):
                ET.SubElement(props, "property", name=f"agentest.coverage.{k}", value=str(ac[k]).lower() if isinstance(ac[k], bool) else str(ac[k]))
            if "signals_missing" in ac:
                ET.SubElement(props, "property", name="agentest.coverage.signals_missing", value=",".join(ac["signals_missing"]))
        if gate_fail:
            tc = ET.SubElement(s, "testcase", classname=f"agentest.{a}", name=instrumentation.RULE_ID)
            msg = instrumentation.message(a, ac)
            ET.SubElement(tc, "failure", message=msg[:500], type="instrumentation-coverage").text = msg
        for i, c in row.items():
            tc = ET.SubElement(s, "testcase", classname=f"agentest.{a}", name=i)
            if c["status"] == "fail":
                ET.SubElement(tc, "failure", message=c["detail"][:500], type="fail").text = c["detail"] + _g(c)
            elif c["status"] != "pass":
                ET.SubElement(tc, "skipped", message=((f"[{c['status']}] " if c["status"] != "n/a" else "") + c["detail"][:500] + _g(c))[:1000])
    return ET.tostring(suites, encoding="unicode", xml_declaration=True)


def to_sarif(res: dict, mode: str = "examples", coverage: dict | None = None) -> dict:
    """SARIF 2.1.0: one rule per catalogue ID, one result per failing (agent, ID) cell.
    The location is the agent's metadata directory (agents/<agent>/). The instrumentation-coverage gate is one more
    rule (agentest/instrumentation-coverage) with an error result per agent above the n/a threshold; the full coverage
    report is in runs[0].properties.instrumentationCoverage."""
    from agentest.standards import instrumentation

    cov = _coverage(res, coverage)
    cat = _catalog()
    ids = sorted({i for row in res.values() for i in row})
    sev = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}
    rules = [{"id": i, "name": i.replace("-", "_"), "shortDescription": {"text": (cat.get(i, {}).get("title") or _what(i) or i)[:200]},
              "fullDescription": {"text": _what(i) or cat.get(i, {}).get("objective", i)},
              "defaultConfiguration": {"level": sev.get(str(cat.get(i, {}).get("severity", "")).lower(), "warning")},
              "properties": {"tags": [t for t in [cat.get(i, {}).get("class_id"), cat.get(i, {}).get("priority")] if t]}} for i in ids]
    index = {i: n for n, i in enumerate(ids)}
    # a finding's own severity (R.severity, e.g. X-020 restricted data only in a tool result) overrides the rule default
    results = [{"ruleId": i, "ruleIndex": index[i], "level": sev.get(str(c.get("severity") or "").lower()) or rules[index[i]]["defaultConfiguration"]["level"],
                "message": {"text": f"{a}: {c['detail']}{_g(c)}"},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": f"agents/{a}/agent-card.json"}}}]}
               for a, row in res.items() for i, c in row.items() if c["status"] == "fail"]
    rules.append({"id": instrumentation.RULE_ID, "name": "instrumentation_coverage",
                  "shortDescription": {"text": "Share of n/a verdicts is within the instrumentation-coverage threshold"},
                  "fullDescription": {"text": f"Fails an agent whose share of n/a + not-run verdicts exceeds max_na_share "
                                              f"(default {instrumentation.DEFAULT_MAX_NA}): its traces carry too little standard instrumentation."},
                  "defaultConfiguration": {"level": "error"}, "properties": {"tags": ["instrumentation"]}})
    results += [{"ruleId": instrumentation.RULE_ID, "ruleIndex": len(rules) - 1, "level": "error",
                 "message": {"text": instrumentation.message(a, cov["agents"][a])},
                 "locations": [{"physicalLocation": {"artifactLocation": {"uri": f"agents/{a}/agent-card.json"}}}]}
                for a in cov["failing"]]
    return {"$schema": SARIF_SCHEMA, "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "agentest", "version": VERSION, "informationUri": "https://github.com/srpadmanabhuni/agentest",
                                          "rules": rules}}, "results": results, "properties": {"mode": mode, "instrumentationCoverage": cov}}]}


def to_markdown(res: dict, mode: str = "examples") -> str:
    tot = {s: sum(c["status"] == s for row in res.values() for c in row.values()) for s in ("pass", "fail", "n/a", "not-assessed")}
    out = [f"# agentest {VERSION} report ({mode} mode)", "", f"{tot['pass']} pass, {tot['fail']} fail, {tot['n/a']} n/a, {tot['not-assessed']} not assessed (no judge) over {len(res)} agent(s).", ""]
    for a, row in res.items():
        out += [f"## {a}", "", "| ID | status | detail | what to do |", "|---|---|---|---|"]
        out += [f"| {i} | {c['status']} | {c['detail'].replace('|', '/')[:200]} | {_g(c)[3:].replace('|', '/')[:400]} |"
                for i, c in sorted(row.items(), key=lambda kv: (kv[1]["status"] != "fail", kv[0]))]
        out.append("")
    return "\n".join(out)


def to_html(res: dict, mode: str = "examples") -> str:
    rows = "".join(f"<tr class='{html.escape(c['status'])}'><td>{html.escape(a)}</td><td>{html.escape(i)}</td><td>{html.escape(c['status'])}</td>"
                   f"<td>{html.escape(c['detail'][:300])}</td><td>{html.escape(_g(c)[3:][:500])}</td></tr>" for a, row in res.items() for i, c in row.items())
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>agentest {VERSION}</title><style>td{{padding:2px 6px}}"
            ".fail{background:#fdd}.pass{background:#dfd}</style></head><body>"
            f"<h1>agentest {VERSION} ({html.escape(mode)} mode)</h1><table><tr><th>agent</th><th>ID</th><th>status</th><th>detail</th><th>what to do</th></tr>{rows}</table></body></html>")


def standards_map() -> dict:
    from pathlib import Path

    import yaml

    return (yaml.safe_load((Path(__file__).with_name("standards_map.yaml")).read_text()) or {}).get("map", {})


def catalog_rows() -> list[dict]:
    """The catalogue (CC BY 4.0) joined with the v3 rule summary and standards mapping, for CSV/JSON export."""
    from agentest.standards.catalog import ALL_IDS
    cat, sm = _catalog(), standards_map()
    rows = []
    for i in ALL_IDS:
        c = cat.get(i, {})
        rows.append({"id": i, "class_id": c.get("class_id", i.split("-")[0]), "title": c.get("title", ""), "severity": c.get("severity", ""),
                     "priority": c.get("priority", ""), "objective": c.get("objective", ""), "acceptance_criteria": c.get("acceptance_criteria", ""),
                     "v3_rule": _what(i), "standards": json.dumps(sm.get(i, {}), sort_keys=True), "licence": "CC BY 4.0" if c else "Apache-2.0 (repo extension)"})
    return rows


def catalog_csv() -> str:
    rows = catalog_rows()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


# ---------------------------------------------------------------- verdicts as OpenTelemetry (OTLP/JSON)

def to_otlp_verdicts(res: dict, mode: str, links: dict[str, list[tuple[str, str]]] | None = None) -> dict:
    """Verdicts as OTLP/JSON: one ``agentest.run`` span per agent, one ``gen_ai.evaluation.result`` event per ID
    (OTel GenAI evaluation event: gen_ai.evaluation.name / score.label / score.value / explanation), with span links to
    the root spans of the judged traces. Send it to any OTel backend next to the agent's own traces."""
    import hashlib

    from agentest import __version__

    def hx(s: str, n: int) -> str:
        return hashlib.sha256(s.encode()).hexdigest()[:n]

    def kv(k: str, v) -> dict:
        val = {"boolValue": v} if isinstance(v, bool) else {"doubleValue": float(v)} if isinstance(v, float) else \
              {"intValue": str(v)} if isinstance(v, int) else {"stringValue": str(v)}
        return {"key": k, "value": val}

    score = {"pass": 1.0, "fail": 0.0}
    spans = []
    t0 = 1_700_000_000_000_000_000
    for i, (agent, row) in enumerate(sorted(res.items())):
        tid = hx(f"agentest-verdicts/{agent}/{mode}", 32)
        tally = {s: sum(c["status"] == s for c in row.values()) for s in ("pass", "fail", "n/a", "not-assessed", "not-run")}
        events = []
        for j, (cid, c) in enumerate(sorted(row.items())):
            attrs = [kv("gen_ai.evaluation.name", cid), kv("gen_ai.evaluation.score.label", c["status"]),
                     kv("gen_ai.evaluation.explanation", c["detail"][:2000])]
            if c["status"] in score:
                attrs.append(kv("gen_ai.evaluation.score.value", score[c["status"]]))
            events.append({"timeUnixNano": str(t0 + i * 1_000_000 + j + 1), "name": "gen_ai.evaluation.result", "attributes": attrs})
        spans.append({"traceId": tid, "spanId": hx(tid, 16), "parentSpanId": "", "name": f"agentest.run {agent}", "kind": 1,
                      "startTimeUnixNano": str(t0 + i * 1_000_000), "endTimeUnixNano": str(t0 + i * 1_000_000 + len(row) + 1),
                      "attributes": [kv("gen_ai.agent.name", agent), kv("agentest.mode", mode), kv("agentest.version", __version__),
                                     *[kv(f"agentest.verdicts.{k.replace('/', '').replace('-', '_')}", v) for k, v in tally.items()]],
                      "events": events,
                      "links": [{"traceId": t, "spanId": s} for t, s in (links or {}).get(agent, [])][:1000],
                      "status": {"code": 2, "message": f"{tally['fail']} failing checks"} if tally["fail"] else {"code": 1}})
    return {"resourceSpans": [{"resource": {"attributes": [kv("service.name", "agentest"), kv("service.version", __version__)]},
                               "scopeSpans": [{"scope": {"name": "agentest.standards.reports", "version": __version__}, "spans": spans}]}]}
