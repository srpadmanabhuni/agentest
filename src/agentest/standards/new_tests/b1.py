"""New tests, batch 1: NT-001..NT-009 (opt-in). Trace attributes in docs/new-tests/b1.md.

Task outcomes and tool use: per-task latency and cost budgets, autonomous step ratio, expected tool per step, goal
relevance of state-changing calls, page extraction, click targets, form filling and API response mapping.
Every check reads recorded trace attributes only; a missing declaration or signal gives ``n/a``, never ``pass``.
"""
# Ref NT-001..NT-009: internal design (catalog/new-tests/b1.jsonl; article tests A002, A003, A004, A006, A007, A008, A009, A010).
# Ref class background: state-based and spec-derived oracles [Barr-2015] [Utting-2012]; trace shape [OTel-GenAI-semconv].

from __future__ import annotations

import json
from typing import Any

from agentest.standards.expr import R, get_path, ok
from agentest.standards.new_tests.common import jattr, median, task
from agentest.standards.otel import Run, usage_tokens
from agentest.standards.rules import Ctx, need, rule

TRUE = ("true", "1", "yes")
BAD_RESPONSE = ("partial", "malformed", "invalid", "truncated")


# ---------------------------------------------------------------- helpers (batch 1 only)

def _truthy(v: Any) -> bool:
    return v is True or (isinstance(v, (int, float)) and not isinstance(v, bool) and v == 1) or str(v).strip().lower() in TRUE


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _list(v: Any) -> list:
    """A declared list: JSON list, a single value, or a comma-separated string."""
    v = jattr({"v": v}, "v")
    if v in (None, ""):
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return [v]


def _dict(v: Any) -> dict:
    v = jattr({"v": v}, "v")
    return v if isinstance(v, dict) else {}


def _same(a: Any, b: Any) -> bool:
    """Value equality across JSON and attribute encodings: numbers by value, text trimmed and case-folded."""
    na, nb = _num(a), _num(b)
    if na is not None and nb is not None:
        return abs(na - nb) <= 1e-9 * max(1.0, abs(na), abs(nb))
    if isinstance(a, (dict, list)) or isinstance(b, (dict, list)):
        return json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)
    return str(a).strip().casefold() == str(b).strip().casefold()


def _tid(r: Run) -> str:
    """The task a run belongs to: agentest.task.id when declared, else the input id (repeated runs share it)."""
    return str(task(r, "id") or r.input_id or r.conversation or "run")


def _steps(r: Run) -> list[dict]:
    """Every span of the run in start order (name, attrs, t0, t1). Runs built without the span list fall back to their
    tool spans, so the checks also read hand-built ``Run`` objects."""
    if r.spans:
        return sorted(r.spans, key=lambda s: s["t0"])
    return [{"name": f"execute_tool {t.name}", "attrs": {"gen_ai.tool.call.result": t.result, **t.attrs,
                                                         "gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": t.name},
             "t0": t.t, "t1": t.t1 or t.t, "error": t.error} for t in sorted(r.tools, key=lambda t: t.t)]


def _is_tool(s: dict) -> bool:
    return s["attrs"].get("gen_ai.operation.name") == "execute_tool"


def _root_seconds(r: Run) -> float | None:
    roots = [s for s in r.spans if not s.get("parent")]
    if roots:
        return (roots[0]["t1"] - roots[0]["t0"]) / 1e9
    if r.duration_s is not None:
        return float(r.duration_s)
    if r.times:
        return (max(t1 for _, t1 in r.times) - min(t0 for t0, _ in r.times)) / 1e9
    return None


def _by_task(runs: list[Run]) -> dict[str, list[Run]]:
    out: dict[str, list[Run]] = {}
    for r in runs:
        out.setdefault(_tid(r), []).append(r)
    return out


def _structured(r: Run) -> dict | None:
    """The run's structured output: ``agentest.output.structured`` on the root span, else a JSON-object final answer."""
    v = jattr(r.attrs, "agentest.output.structured")
    if isinstance(v, dict):
        return v
    try:
        a = json.loads((r.answer or "").strip())
    except ValueError:
        return None
    return a if isinstance(a, dict) else None


def _json(x: Any) -> Any:
    if isinstance(x, (dict, list)):
        return x
    try:
        return json.loads(x) if isinstance(x, str) and x.strip() else None
    except ValueError:
        return None


def _key_values(x: Any, key: str) -> list:
    """Every value stored under ``key`` anywhere inside a JSON value."""
    out = []
    if isinstance(x, dict):
        for k, v in x.items():
            if k == key:
                out.append(v)
            out += _key_values(v, key)
    elif isinstance(x, list):
        for v in x:
            out += _key_values(v, key)
    return out


def _verdict(bad: list[str], n: int, what: str) -> R:
    need(n, f"no {what}")
    return ok(not bad, "; ".join(bad[:5]) if bad else f"{n} {what} checked")


# ---------------------------------------------------------------- NT-001 / NT-002 budgets (A002)

# Ref NT-001: internal design (catalog/new-tests/b1.jsonl NT-001; article test A002)
@rule("NT-001", what="Per-task latency within the declared budget: for each task with agentest.task.budget.latency_s, the median over its runs of root-span duration / budget is <= 1.")
def _nt_001(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for t, rs in _by_task(c.runs).items():
        ratios = []
        for r in rs:
            b, d = _num(task(r, "budget.latency_s")), _root_seconds(r)
            if b and b > 0 and d is not None:
                ratios.append(d / b)
        if not ratios:
            continue
        n += 1
        m = median(ratios)
        if m > 1:
            bad.append(f"{t}: median latency {m:.2f}x the budget over {len(ratios)} run(s)")
    return _verdict(bad, n, "task with a latency budget and a recorded duration")


def _usage(r: Run) -> tuple[float | None, float | None]:
    """(tokens, cost) of one run. Tokens use :func:`usage_tokens`. Cost is summed the same way: children first, else root."""
    def tot_cost(spans: list[dict]) -> float | None:
        cost = None
        for s in spans:
            v = _num(s["attrs"].get("agentest.usage.cost"))
            if v is not None:
                cost = (cost or 0) + v
        return cost
    if r.spans:
        root = [s for s in r.spans if not s.get("parent")][:1]
        kids = [s for s in r.spans if s not in root]
        ck, cr = tot_cost(kids), tot_cost(root)
        cost = ck if ck is not None else cr
    else:
        cost = tot_cost([{"attrs": r.attrs}] + _steps(r))
    return usage_tokens(r), cost


# Ref NT-002: internal design (catalog/new-tests/b1.jsonl NT-002; article test A002)
@rule("NT-002", what="Per-task token and compute cost within the declared budget: per task, the median over runs of summed gen_ai.usage input+output tokens (and agentest.usage.cost) is <= agentest.task.budget.tokens (and .cost).")
def _nt_002(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for t, rs in _by_task(c.runs).items():
        for key, idx, label in (("budget.tokens", 0, "tokens"), ("budget.cost", 1, "cost")):
            vals, b = [], None
            for r in rs:
                b_r = _num(task(r, key))
                u = _usage(r)[idx]
                if b_r is not None and b_r > 0 and u is not None:
                    b = b_r if b is None else min(b, b_r)
                    vals.append(u)
            if not vals:
                continue
            n += 1
            m = median(vals)
            if m > b:
                bad.append(f"{t}: median {label} {m:g} > budget {b:g} over {len(vals)} run(s)")
    return _verdict(bad, n, "task with a token or cost budget and recorded usage")


# ---------------------------------------------------------------- NT-003 autonomous step ratio (A003)

def _human_steps(r: Run) -> tuple[int, int]:
    """(autonomous tool steps, all tool steps). A tool step is human-assisted when it carries agentest.step.human_input=true
    or an ``agentest.human_input`` span starts after the previous tool step and before it."""
    auto = total = 0
    human_pending = False
    for s in _steps(r):
        a = s["attrs"]
        if s["name"] == "agentest.human_input" or a.get("gen_ai.operation.name") == "agentest.human_input":
            human_pending = True
            continue
        if not _is_tool(s):
            continue
        total += 1
        if not (human_pending or _truthy(a.get("agentest.step.human_input"))):
            auto += 1
        human_pending = False
    return auto, total


# Ref NT-003: internal design (catalog/new-tests/b1.jsonl NT-003; article test A003)
@rule("NT-003", what="Autonomous step ratio meets the declared autonomy level: per task, the share of tool steps without a preceding human-input span (or agentest.step.human_input=true) is within agentest.task.autonomy_tolerance (default 0.05) of agentest.task.autonomy_level.")
def _nt_003(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for t, rs in _by_task(c.runs).items():
        lvl = next((_num(task(r, "autonomy_level")) for r in rs if _num(task(r, "autonomy_level")) is not None), None)
        if lvl is None:
            continue
        lvl = lvl / 100 if lvl > 1 else lvl  # a percentage
        tol = next((_num(task(r, "autonomy_tolerance")) for r in rs if _num(task(r, "autonomy_tolerance")) is not None), 0.05)
        auto = total = 0
        for r in rs:
            a, k = _human_steps(r)
            auto, total = auto + a, total + k
        if not total:
            continue
        n += 1
        ratio = auto / total
        if abs(ratio - lvl) > tol + 1e-9:
            bad.append(f"{t}: autonomous ratio {ratio:.2f} ({auto}/{total}) vs declared {lvl:.2f} +/- {tol:.2f}")
    return _verdict(bad, n, "task with a declared autonomy level and tool steps")


# ---------------------------------------------------------------- NT-004 expected tool per step (A004)

# Ref NT-004: internal design (catalog/new-tests/b1.jsonl NT-004; article test A004)
@rule("NT-004", what="Expected tool chosen at each step: every tool span labelled agentest.step.expected_tool calls that tool or one listed in agentest.step.acceptable_tools.")
def _nt_004(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for r in c.runs:
        for s in _steps(r):
            a = s["attrs"]
            want = a.get("agentest.step.expected_tool")
            if not _is_tool(s) or want in (None, ""):
                continue
            n += 1
            ok_names = {str(want)} | {str(x) for x in _list(a.get("agentest.step.acceptable_tools"))}
            got = a.get("gen_ai.tool.name", "")
            if got not in ok_names:
                bad.append(f"{_tid(r)}: called {got!r}, expected {sorted(ok_names)}")
    return _verdict(bad, n, "labelled tool step")


# ---------------------------------------------------------------- NT-005 goal relevance (A006)

# Ref NT-005: internal design (catalog/new-tests/b1.jsonl NT-005; article test A006)
@rule("NT-005", what="Actions stay relevant to the stated goal: on runs not marked agentest.input.attack=true, every succeeded state-changing tool call (MCP readOnlyHint false) is in agentest.task.allowed_actions.")
def _nt_005(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for r in c.runs:
        if _truthy(r.attrs.get("agentest.input.attack")):
            continue
        allowed = task(r, "allowed_actions")
        if allowed in (None, ""):
            continue
        allowed = {str(x) for x in _list(allowed)}
        for t in c.ok_writes(r):
            n += 1
            if t.name not in allowed:
                bad.append(f"{_tid(r)}: state-changing call {t.name!r} not in the allowed actions")
    return _verdict(bad, n, "succeeded state-changing call on a run with declared allowed actions")


# ---------------------------------------------------------------- NT-006 page extraction (A007)

# Ref NT-006: internal design (catalog/new-tests/b1.jsonl NT-006; article test A007)
@rule("NT-006", what="Extracted page values match the page snapshot: each extracted field (agentest.task.extracted names; values from agentest.output.structured or a JSON answer) equals the same field in a page-snapshot tool result (agentest.tool.kind=page_snapshot); a field absent from every snapshot fails.")
def _nt_006(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for r in c.runs:
        snaps = [_json(s["attrs"].get("gen_ai.tool.call.result")) for s in _steps(r)
                 if _is_tool(s) and s["attrs"].get("agentest.tool.kind") == "page_snapshot" and not s.get("error")]
        snaps = [x for x in snaps if isinstance(x, (dict, list))]
        out = _structured(r)
        if not snaps or out is None:
            continue
        fields = [str(f) for f in _list(task(r, "extracted"))] or list(out)
        for f in fields:
            n += 1
            if f not in out or out[f] in (None, ""):
                bad.append(f"{_tid(r)}: field {f!r} not extracted")
                continue
            seen = [v for x in snaps for v in _key_values(x, f)]
            if not seen:
                bad.append(f"{_tid(r)}: field {f!r} is not on any page snapshot (invented)")
            elif not any(_same(out[f], v) for v in seen):
                bad.append(f"{_tid(r)}: field {f!r}={out[f]!r} differs from the page ({seen[0]!r})")
    return _verdict(bad, n, "extracted field with a page snapshot")


# ---------------------------------------------------------------- NT-007 click target (A008)

# Ref NT-007: internal design (catalog/new-tests/b1.jsonl NT-007; article test A008)
@rule("NT-007", what="Click lands on the intended element: every span with agentest.ui.action=click and agentest.ui.expected_element_id has an equal agentest.ui.element_id.")
def _nt_007(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for r in c.runs:
        for s in _steps(r):
            a = s["attrs"]
            if str(a.get("agentest.ui.action", "")).lower() != "click":
                continue
            want, got = a.get("agentest.ui.expected_element_id"), a.get("agentest.ui.element_id")
            if want in (None, "") or got in (None, ""):
                continue  # no intended element or no recorded target: not checkable
            n += 1
            if str(want).strip() != str(got).strip():
                bad.append(f"{_tid(r)}: clicked {got!r}, intended {want!r}")
    return _verdict(bad, n, "click with an intended and a recorded element")


# ---------------------------------------------------------------- NT-008 form filling (A009)

def _form_spans(r: Run) -> list[dict]:
    return [s for s in _steps(r) if s["attrs"].get("agentest.form.id") not in (None, "")]


def _is_submit(a: dict) -> bool:
    return "submit" in (str(a.get("agentest.form.action", "")).lower(), str(a.get("agentest.ui.action", "")).lower())


def _errors(a: dict) -> list:
    return _list(a.get("agentest.form.validation_errors"))


# Ref NT-008: internal design (catalog/new-tests/b1.jsonl NT-008; article test A009)
@rule("NT-008", what="Forms filled correctly: the final submit per agentest.form.id carries the agentest.task.expected_form values without validation errors; every submit with agentest.form.validation_errors is followed by a resubmit; agentest.form.step values are non-decreasing and complete.")
def _nt_008(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for r in c.runs:
        fs = _form_spans(r)
        exp = _dict(task(r, "expected_form"))
        if exp and not all(isinstance(v, dict) for v in exp.values()):  # one form: {field: value}
            ids = {str(s["attrs"]["agentest.form.id"]) for s in fs}
            exp = {next(iter(ids)): exp} if len(ids) == 1 else {"": exp}
        totals = _dict(task(r, "form_steps"))
        forms = {str(s["attrs"]["agentest.form.id"]) for s in fs} | set(exp)
        if not fs and not exp:
            continue
        for fid in sorted(forms):
            mine = [s for s in fs if str(s["attrs"]["agentest.form.id"]) == fid]
            subs = [s for s in mine if _is_submit(s["attrs"])]
            n += 1
            if fid in exp:
                if not subs:
                    bad.append(f"{_tid(r)}: form {fid!r} never submitted")
                    continue
                vals = _dict(subs[-1]["attrs"].get("agentest.form.values"))
                wrong = [k for k, v in exp[fid].items() if k not in vals or not _same(vals[k], v)]
                if wrong:
                    bad.append(f"{_tid(r)}: form {fid!r} final submit has wrong or missing fields {wrong}")
            for i, s in enumerate(subs):
                if _errors(s["attrs"]) and i == len(subs) - 1:
                    bad.append(f"{_tid(r)}: form {fid!r} validation errors {_errors(s['attrs'])} not corrected by a resubmit")
            steps = [int(x) for x in (_num(s["attrs"].get("agentest.form.step")) for s in mine) if x is not None]
            if steps:
                if any(b < a for a, b in zip(steps, steps[1:], strict=False)):
                    bad.append(f"{_tid(r)}: form {fid!r} steps out of order {steps}")
                last = int(_num(totals.get(fid)) or 0) or int(_num(mine[-1]["attrs"].get("agentest.form.steps_total")) or 0) or max(steps)
                missing = sorted(set(range(1, last + 1)) - set(steps))
                if missing:
                    bad.append(f"{_tid(r)}: form {fid!r} steps {missing} skipped")
    return _verdict(bad, n, "form with recorded fields or a declared expected form")


# ---------------------------------------------------------------- NT-009 API response mapping (A010)

def _bad_response(s: dict) -> str:
    st = str(s["attrs"].get("agentest.api.response_status", "")).strip().lower()
    if st in BAD_RESPONSE:
        return st
    if s.get("error"):
        return "error"
    return "" if isinstance(_json(s["attrs"].get("gen_ai.tool.call.result")), (dict, list)) else "unparsable"


# Ref NT-009: internal design (catalog/new-tests/b1.jsonl NT-009; article test A010)
@rule("NT-009", what="API responses mapped to the expected schema: for agentest.task.output_mapping {field: {tool, path}}, the output field equals the value at path in that tool's last result; when that response is partial, malformed or unparsable the field is left empty and listed in agentest.output.flagged.")
def _nt_009(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for r in c.runs:
        mp = _dict(task(r, "output_mapping"))
        out = _structured(r)
        if not mp or out is None:
            continue
        flagged = {str(x) for x in _list(r.attrs.get("agentest.output.flagged"))}
        tools = [s for s in _steps(r) if _is_tool(s)]
        for field_name, spec in mp.items():
            if not isinstance(spec, dict) or not spec.get("tool"):
                continue
            src = [s for s in tools if s["attrs"].get("gen_ai.tool.name") == spec["tool"]]
            if not src:
                continue  # the source API was not called in this run
            n += 1
            last, got = src[-1], out.get(field_name)
            why = _bad_response(last)
            if why:
                if got not in (None, ""):
                    bad.append(f"{_tid(r)}: {field_name!r} uses a {why} {spec['tool']} response")
                elif not ({field_name, str(spec["tool"])} & flagged):
                    bad.append(f"{_tid(r)}: {why} {spec['tool']} response for {field_name!r} not flagged")
                continue
            want = get_path(_json(last["attrs"].get("gen_ai.tool.call.result")), str(spec.get("path", field_name)))
            if want is None:  # the response does not follow the expected schema: same duty as a malformed response
                if got not in (None, "") or not ({field_name, str(spec["tool"])} & flagged):
                    bad.append(f"{_tid(r)}: path {spec.get('path')!r} missing in the {spec['tool']} response and {field_name!r} not flagged")
            elif got is None or not _same(got, want):
                bad.append(f"{_tid(r)}: {field_name!r}={got!r}, response has {want!r}")
    return _verdict(bad, n, "mapped output field with a source API response")
