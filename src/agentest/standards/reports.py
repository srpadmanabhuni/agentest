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


def to_versioned_json(res: dict, mode: str) -> dict:
    return {"schema": SCHEMA_ID, "$schema": VERDICTS_SCHEMA, "tool": {"name": "agentest", "version": VERSION}, "mode": mode,
            "results": [{"agent": a, "id": i, "status": c["status"], "detail": c["detail"]} for a, row in res.items() for i, c in row.items()]}


def to_junit(res: dict, mode: str = "examples") -> str:
    """JUnit XML: one <testsuite> per agent, one <testcase> per ID. fail -> <failure>, n/a -> <skipped>."""
    suites = ET.Element("testsuites", name=f"agentest {VERSION} ({mode})")
    for a, row in res.items():
        f = sum(c["status"] == "fail" for c in row.values())
        sk = sum(c["status"] not in ("pass", "fail") for c in row.values())
        s = ET.SubElement(suites, "testsuite", name=a, tests=str(len(row)), failures=str(f), errors="0", skipped=str(sk))
        for i, c in row.items():
            tc = ET.SubElement(s, "testcase", classname=f"agentest.{a}", name=i)
            if c["status"] == "fail":
                ET.SubElement(tc, "failure", message=c["detail"][:500], type="fail").text = c["detail"]
            elif c["status"] != "pass":
                ET.SubElement(tc, "skipped", message=c["detail"][:500])
    return ET.tostring(suites, encoding="unicode", xml_declaration=True)


def to_sarif(res: dict, mode: str = "examples") -> dict:
    """SARIF 2.1.0: one rule per catalogue ID, one result per failing (agent, ID) cell.
    The location is the agent's metadata directory (agents/<agent>/)."""
    cat = _catalog()
    ids = sorted({i for row in res.values() for i in row})
    sev = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}
    rules = [{"id": i, "name": i.replace("-", "_"), "shortDescription": {"text": (cat.get(i, {}).get("title") or _what(i) or i)[:200]},
              "fullDescription": {"text": _what(i) or cat.get(i, {}).get("objective", i)},
              "defaultConfiguration": {"level": sev.get(str(cat.get(i, {}).get("severity", "")).lower(), "warning")},
              "properties": {"tags": [t for t in [cat.get(i, {}).get("class_id"), cat.get(i, {}).get("priority")] if t]}} for i in ids]
    index = {i: n for n, i in enumerate(ids)}
    results = [{"ruleId": i, "ruleIndex": index[i], "level": rules[index[i]]["defaultConfiguration"]["level"],
                "message": {"text": f"{a}: {c['detail']}"},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": f"agents/{a}/agent-card.json"}}}]}
               for a, row in res.items() for i, c in row.items() if c["status"] == "fail"]
    return {"$schema": SARIF_SCHEMA, "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "agentest", "version": VERSION, "informationUri": "https://github.com/srpadmanabhuni/agentest",
                                          "rules": rules}}, "results": results, "properties": {"mode": mode}}]}


def to_markdown(res: dict, mode: str = "examples") -> str:
    tot = {s: sum(c["status"] == s for row in res.values() for c in row.values()) for s in ("pass", "fail", "n/a")}
    out = [f"# agentest {VERSION} report ({mode} mode)", "", f"{tot['pass']} pass, {tot['fail']} fail, {tot['n/a']} n/a over {len(res)} agent(s).", ""]
    for a, row in res.items():
        out += [f"## {a}", "", "| ID | status | detail |", "|---|---|---|"]
        out += [f"| {i} | {c['status']} | {c['detail'].replace('|', '/')[:200]} |" for i, c in sorted(row.items(), key=lambda kv: (kv[1]["status"] != "fail", kv[0]))]
        out.append("")
    return "\n".join(out)


def to_html(res: dict, mode: str = "examples") -> str:
    rows = "".join(f"<tr class='{html.escape(c['status'])}'><td>{html.escape(a)}</td><td>{html.escape(i)}</td><td>{html.escape(c['status'])}</td>"
                   f"<td>{html.escape(c['detail'][:300])}</td></tr>" for a, row in res.items() for i, c in row.items())
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>agentest {VERSION}</title><style>td{{padding:2px 6px}}"
            ".fail{background:#fdd}.pass{background:#dfd}</style></head><body>"
            f"<h1>agentest {VERSION} ({html.escape(mode)} mode)</h1><table><tr><th>agent</th><th>ID</th><th>status</th><th>detail</th></tr>{rows}</table></body></html>")


def standards_map() -> dict:
    from pathlib import Path

    import yaml

    return (yaml.safe_load((Path(__file__).with_name("standards_map.yaml")).read_text()) or {}).get("map", {})


def catalog_rows() -> list[dict]:
    """The catalogue (CC BY 4.0) joined with the v3 rule summary and standards mapping, for CSV/JSON export."""
    from agentest.real.ids import ALL_IDS
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
