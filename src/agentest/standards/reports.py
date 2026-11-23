"""Open output formats for verdicts: versioned JSON, JUnit XML, SARIF 2.1.0, Markdown and HTML.

All writers take the plain verdict mapping ``{agent: {id: {"status", "detail"}}}`` produced by
``runner.to_json`` and use only the standard library. Markdown, HTML and versioned JSON can also
carry a Trials section computed from the judged runs. That section does not change any check verdict.
"""
# Ref: [SARIF-2.1.0] (SARIF output); JSON verdict schema is internal design (src/agentest/standards/schemas/verdicts.schema.json).

from __future__ import annotations

import csv
import html
import io
import json
import math
from xml.etree import ElementTree as ET

from agentest.standards import VERSION

VERDICTS_SCHEMA = "https://github.com/srpadmanabhuni/agentest/blob/main/src/agentest/standards/schemas/verdicts.schema.json"
SCHEMA_ID = "agentest.verdicts/1"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
# Below this trial count the normal approximation behind the standard error is thin.
SMALL_K = 30
SMALL_K_NOTE = "k is small; the standard error is a rough guide"


def pass_at_k(n: int, passes: int, k: int) -> float:
    """Unbiased estimator of the chance that at least one of ``k`` drawn trials succeeds.

    ``1 - C(n - passes, k) / C(n, k)``. When ``n - passes < k`` a draw of ``k`` failures is
    impossible, so the value is 1. With ``k == n`` this is 1 when any trial succeeded and 0 otherwise.
    """
    if k < 1 or n < k or passes < 0 or passes > n:
        raise ValueError(f"pass@k needs 1 <= k <= n and 0 <= passes <= n, got n={n} passes={passes} k={k}")
    if n - passes < k:
        return 1.0
    return 1.0 - math.comb(n - passes, k) / math.comb(n, k)


def pass_all_k(n: int, passes: int, k: int) -> float:
    """Estimator of the chance that every one of ``k`` drawn trials succeeds: ``C(passes, k) / C(n, k)``.

    With ``k == n`` this is 1 when every trial succeeded and 0 otherwise.
    """
    if k < 1 or n < k or passes < 0 or passes > n:
        raise ValueError(f"pass^k needs 1 <= k <= n and 0 <= passes <= n, got n={n} passes={passes} k={k}")
    if passes < k:
        return 0.0
    return math.comb(passes, k) / math.comb(n, k)


def success_rate_se(k: int, passes: int) -> float:
    """Standard error of the success rate ``passes / k``."""
    if k < 1 or passes < 0 or passes > k:
        raise ValueError(f"standard error needs k >= 1 and 0 <= passes <= k, got k={k} passes={passes}")
    p = passes / k
    return math.sqrt(p * (1.0 - p) / k)


def _task_id(run) -> str:
    """Group repeated runs the way the per-task checks do: ``agentest.task.id``, else the input id."""
    from agentest.standards.new_tests.common import jattr

    declared = jattr(run.attrs, "agentest.task.id")
    if declared not in (None, ""):
        return str(declared)
    return str(run.input_id or run.conversation or "run")


def _fmt_metric(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def trial_rows(agent_name: str, agent, runs: list, mode: str = "examples") -> list[dict]:
    """One row per task that has more than one run.

    A trial passes when its postconditions hold (the same success signal the outcome checks use).
    ``pass@k`` and ``pass^k`` use the trial count as the draw size. ``k`` below ``SMALL_K`` sets ``note``.
    """
    from agentest.standards.rules import Ctx, _postconditions

    ctx = Ctx(agent, runs, mode)
    order: list[str] = []
    groups: dict[str, list] = {}
    for run in runs:
        tid = _task_id(run)
        if tid not in groups:
            order.append(tid)
            groups[tid] = []
        groups[tid].append(run)
    rows = []
    for tid in order:
        group = groups[tid]
        k = len(group)
        if k < 2:
            continue
        passes = sum(1 for run in group if _postconditions(ctx, run)[0] is True)
        rows.append({
            "agent": agent_name,
            "task": tid,
            "k": k,
            "passes": passes,
            "pass@k": pass_at_k(k, passes, k),
            "pass^k": pass_all_k(k, passes, k),
            "success_rate_se": success_rate_se(k, passes),
            "note": SMALL_K_NOTE if k < SMALL_K else "",
        })
    return rows


def _trials_preamble() -> str:
    return (
        "Trials group runs that share `agentest.task.id` (otherwise the input id). "
        "A trial passes when its postconditions hold. "
        "pass@k is 1 when at least one of the k trials passes and 0 when none do. "
        "pass^k is 1 when every trial passes and 0 otherwise. "
        "With the trial count as the draw size those are `1 - C(k - passes, k) / C(k, k)` and "
        "`C(passes, k) / C(k, k)`. "
        "SE is the standard error of the success rate, passes/k. "
        "When k is small the note says the standard error is a rough guide."
    )


def _catalog() -> dict[str, dict]:
    from agentest.standards.hub import catalogue_file

    out = {}
    p = catalogue_file()  # vendored copy unless AGENTEST_HUB_CATALOGUE=1 (pinned, sha256-checked, cached)
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                d = json.loads(ln)
                out[d["id"]] = d
    return out


def _what(tid: str) -> str:
    from agentest.standards.rules import RULES

    return RULES[tid][0] if tid in RULES else ""


def to_versioned_json(res: dict, mode: str, trials: list[dict] | None = None) -> dict:
    doc = {"schema": SCHEMA_ID, "$schema": VERDICTS_SCHEMA, "tool": {"name": "agentest", "version": VERSION}, "mode": mode,
           "results": [{"agent": a, "id": i, "status": c["status"], "detail": c["detail"]} for a, row in res.items() for i, c in row.items()]}
    if trials:
        doc["trials"] = trials
    return doc


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


def _trials_markdown(trials: list[dict] | None) -> list[str]:
    if not trials:
        return []
    out = ["## Trials", "", _trials_preamble(), "",
           "| agent | task | k | passes | pass@k | pass^k | SE | note |",
           "|---|---|---:|---:|---:|---:|---:|---|"]
    for row in trials:
        cells = [row["agent"], row["task"], str(row["k"]), str(row["passes"]),
                 _fmt_metric(row["pass@k"]), _fmt_metric(row["pass^k"]), _fmt_metric(row["success_rate_se"]),
                 row.get("note") or ""]
        out.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    out.append("")
    return out


def to_markdown(res: dict, mode: str = "examples", trials: list[dict] | None = None) -> str:
    tot = {s: sum(c["status"] == s for row in res.values() for c in row.values()) for s in ("pass", "fail", "n/a")}
    out = [f"# agentest {VERSION} report ({mode} mode)", "", f"{tot['pass']} pass, {tot['fail']} fail, {tot['n/a']} n/a over {len(res)} agent(s).", ""]
    for a, row in res.items():
        out += [f"## {a}", "", "| ID | status | detail |", "|---|---|---|"]
        out += [f"| {i} | {c['status']} | {c['detail'].replace('|', '/')[:200]} |" for i, c in sorted(row.items(), key=lambda kv: (kv[1]["status"] != "fail", kv[0]))]
        out.append("")
    out += _trials_markdown(trials)
    return "\n".join(out)


def _trials_html(trials: list[dict] | None) -> str:
    if not trials:
        return ""
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(text)}</td>" for text in (
            row["agent"], row["task"], str(row["k"]), str(row["passes"]),
            _fmt_metric(row["pass@k"]), _fmt_metric(row["pass^k"]), _fmt_metric(row["success_rate_se"]),
            row.get("note") or "")) + "</tr>"
        for row in trials)
    return ("<h2>Trials</h2><p>" + html.escape(_trials_preamble()) + "</p>"
            "<table><tr><th>agent</th><th>task</th><th>k</th><th>passes</th><th>pass@k</th><th>pass^k</th><th>SE</th><th>note</th></tr>"
            f"{body}</table>")


def to_html(res: dict, mode: str = "examples", trials: list[dict] | None = None) -> str:
    rows = "".join(f"<tr class='{html.escape(c['status'])}'><td>{html.escape(a)}</td><td>{html.escape(i)}</td><td>{html.escape(c['status'])}</td>"
                   f"<td>{html.escape(c['detail'][:300])}</td></tr>" for a, row in res.items() for i, c in row.items())
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>agentest {VERSION}</title><style>td{{padding:2px 6px}}"
            ".fail{background:#fdd}.pass{background:#dfd}</style></head><body>"
            f"<h1>agentest {VERSION} ({html.escape(mode)} mode)</h1><table><tr><th>agent</th><th>ID</th><th>status</th><th>detail</th></tr>{rows}</table>"
            f"{_trials_html(trials)}</body></html>")


def standards_map() -> dict:
    from pathlib import Path

    import yaml

    return (yaml.safe_load((Path(__file__).with_name("standards_map.yaml")).read_text(encoding="utf-8")) or {}).get("map", {})


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
        tally = {s: sum(c["status"] == s for c in row.values()) for s in ("pass", "fail", "n/a", "not-run")}
        events = []
        for j, (cid, c) in enumerate(sorted(row.items())):
            attrs = [kv("gen_ai.evaluation.name", cid), kv("gen_ai.evaluation.score.label", c["status"]),
                     kv("gen_ai.evaluation.explanation", c["detail"][:2000])]
            if c["status"] in score:
                attrs.append(kv("gen_ai.evaluation.score.value", score[c["status"]]))
            events.append({"timeUnixNano": str(t0 + i * 1_000_000 + j + 1), "name": "gen_ai.evaluation.result", "attributes": attrs})
        spans.append({"traceId": tid, "spanId": hx(tid, 16), "parentSpanId": "", "name": f"agentest.run {agent}", "kind": 1,
                      "startTimeUnixNano": str(t0 + i * 1_000_000), "endTimeUnixNano": str(t0 + i * 1_000_000 + len(row) + 1),
                      "attributes": [kv("gen_ai.agent.name", agent), kv("agentest.mode", mode), kv("agentest.version", VERSION),
                                     *[kv(f"agentest.verdicts.{k.replace('/', '').replace('-', '_')}", v) for k, v in tally.items()]],
                      "events": events,
                      "links": [{"traceId": t, "spanId": s} for t, s in (links or {}).get(agent, [])][:1000],
                      "status": {"code": 2, "message": f"{tally['fail']} failing checks"} if tally["fail"] else {"code": 1}})
    return {"resourceSpans": [{"resource": {"attributes": [kv("service.name", "agentest"), kv("service.version", VERSION)]},
                               "scopeSpans": [{"scope": {"name": "agentest.standards.reports", "version": VERSION}, "spans": spans}]}]}
