"""Phase 1 New tests, batch 3: NT-015..NT-019, NT-028, NT-029 (opt-in). Trace attributes in docs/new-tests/b3.md.

Explanations and decision records: stepwise rationale for high-impact calls, answers to "why" probes, structured
knowledge lookups, principal reasons, decision notices, reconstructable decision records. Every check reads recorded
trace attributes only (any agent, any framework); a check whose attributes are missing reports n/a, never pass.

Batch 3 also ships the existing opt-in rules T1-020 (undo) and T1-021 (refusal explanation) as part of the Phase 1
set: their logic is unchanged and they stay out of the default 130 (see ``PHASE1_SHIPPED``).
"""
# Ref NT-015..NT-019, NT-028, NT-029: internal design (catalog/new-tests/b3.jsonl; article tests A029, A031, A033,
# A034, A035, A089, A105).

from __future__ import annotations

import json
import re
from typing import Any

from agentest.standards.expr import R, ok
from agentest.standards.new_tests.common import flat_values, jattr, task, tattr
from agentest.standards.otel import Run, ToolSpan, _text_of
from agentest.standards.rules import Ctx, need, rule

# Existing opt-in rules that Phase 1 ships alongside the New tests (IDs, logic and opt-in status unchanged).
# Run the full Phase 1 set with: agentest std run --ids NT  (includes T1-020, T1-021)
PHASE1_SHIPPED = ("T1-020", "T1-021")
PHASE1_SHIPPED_CLOSES = {"T1-020": ("A023",), "T1-021": ("A031",)}  # A031 closes with T1-021 and NT-016

_TRUE = (True, 1, "true", "True", "TRUE", "1", "yes")


# ---------------------------------------------------------------- helpers (batch-local)

def _true(v: Any) -> bool:
    return v in _TRUE


def _canon(v: Any) -> str:
    """One normalised form per scalar: numbers compare by value ("5000", 5000, 5000.0), strings by trimmed lower case."""
    if isinstance(v, bool):
        return str(v).lower()
    s = str(v).strip().lower()
    num = s.replace(",", "")
    if num and num.lstrip("-").replace(".", "", 1).isdigit():
        f = float(num)
        return repr(int(f)) if f == int(f) else repr(f)
    return s


def _scalars(x: Any) -> list[str]:
    """Every scalar inside a JSON-like value (JSON strings decoded), canonicalised."""
    return [_canon(v) for v in flat_values(x if not isinstance(x, bool) else str(x).lower())]


def _meaningful(vals: list[str]) -> list[str]:
    """Values worth citing: drop empties, single characters and booleans."""
    return [v for v in vals if len(v) >= 2 and v not in ("true", "false", "none", "null")]


def _mentions(text: str, vals: list[str]) -> list[str]:
    """Values from ``vals`` that the text cites (word-bounded, case-insensitive; numbers by value)."""
    t = str(text or "").lower()
    nums = {_canon(n) for n in re.findall(r"-?\d[\d,]*(?:\.\d+)?", t)}
    out = []
    for v in _meaningful(vals):
        if v in nums or re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", t):
            out.append(v)
    return out


def _text(v: Any) -> str:
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return "" if v is None else str(v)


def _result(t: ToolSpan) -> Any:
    try:
        return json.loads(t.result) if t.result and t.result[:1] in "[{" else t.result
    except ValueError:
        return t.result


def _key_values(x: Any, key: str) -> list[str]:
    """Values stored under ``key`` anywhere inside a JSON-like value."""
    out: list[str] = []
    if isinstance(x, str) and x[:1] in "[{":
        try:
            x = json.loads(x)
        except ValueError:
            return out
    if isinstance(x, dict):
        for k, v in x.items():
            if str(k).lower() == key.lower() and not isinstance(v, (dict, list)):
                out.append(_canon(v))
            out += _key_values(v, key)
    elif isinstance(x, list):
        for v in x:
            out += _key_values(v, key)
    return out


def _sources_before(r: Run, t: int | None) -> tuple[list[str], set[str]]:
    """Recorded inputs before time ``t``: scalar values of the user input, earlier tool arguments and results, and the
    ids / names of those earlier calls (what a rationale may reference)."""
    vals = _scalars(r.input) + [_canon(w) for w in re.findall(r"[\w.@-]+", r.input or "")]
    refs = {"input", "user_input"}
    for x in r.tools:
        if t is not None and x.t >= t:
            continue
        vals += _scalars(x.args) + _scalars(_result(x))
        refs |= {x.call_id, x.name} - {""}
    return vals, refs


def _decisions(r: Run) -> list[dict]:
    """Decision records: spans named ``agentest.decision`` or carrying ``agentest.decision.outcome``."""
    out = []
    for i, s in enumerate(r.spans):
        a = s["attrs"]
        if s["name"] != "agentest.decision" and "agentest.decision.outcome" not in a:
            continue
        d = {k[len("agentest.decision."):]: jattr(a, k) for k in a if k.startswith("agentest.decision.")}
        d.setdefault("id", s.get("id") or f"d{i}")
        d["_t"] = s["t0"]
        out.append(d)
    return out


def _as_keys(x: Any) -> set[str]:
    """Names of inputs / criteria: dict keys, list items (strings, or the 'id'/'name' of dicts)."""
    if isinstance(x, dict):
        return {str(k).lower() for k in x}
    if isinstance(x, list):
        ks = set()
        for v in x:
            if isinstance(v, dict):
                ks |= {str(v[k]).lower() for k in ("id", "name") if v.get(k) not in (None, "")}
            elif v not in (None, ""):
                ks.add(str(v).lower())
        return ks
    return set()


def _reason_refs(reason: Any) -> list[str] | None:
    """Explicit references of one reason (keys 'input(s)', 'criterion'/'criteria', 'ref(s)'); None when the reason is
    free text."""
    if not isinstance(reason, dict):
        return None
    refs: list[str] = []
    for k in ("input", "inputs", "criterion", "criteria", "ref", "refs"):
        v = reason.get(k)
        if isinstance(v, list):
            refs += [str(x).lower() for x in v if x not in (None, "")]
        elif v not in (None, ""):
            refs.append(str(v).lower())
    return refs


def _reason_text(reason: Any) -> str:
    if isinstance(reason, dict):
        return str(reason.get("text") or reason.get("reason") or "")
    return str(reason or "")


def _reason_grounded(reason: Any, keys: set[str], values: list[str]) -> tuple[bool, str]:
    """A reason is grounded when its explicit refs all name present keys (and at least one is given), or, for a
    free-text reason, when it names a present key or cites a present value."""
    refs = _reason_refs(reason)
    if refs is not None and refs:
        missing = [x for x in refs if x not in keys]
        return not missing, f"refers to absent {missing}" if missing else ""
    txt = _reason_text(reason)
    if not txt.strip():
        return False, "empty reason"
    low = txt.lower().replace("_", " ")
    hit = [k for k in keys if re.search(r"(?<![a-z0-9])" + re.escape(k.replace("_", " ")) + r"(?![a-z0-9])", low)]
    good = bool(hit or _mentions(txt, values))
    return good, "" if good else f"'{txt[:40]}' names no recorded input"


def _list(x: Any) -> list:
    if x in (None, ""):
        return []
    return x if isinstance(x, list) else [x]


def _get(d: Any, path: str) -> Any:
    for p in str(path).split("."):
        if isinstance(d, dict) and p in d:
            d = d[p]
        elif isinstance(d, list) and p.isdigit() and int(p) < len(d):
            d = d[int(p)]
        else:
            return None
    return d


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, (dict, list)) or isinstance(b, (dict, list)):
        return sorted(_scalars(a)) == sorted(_scalars(b))
    return _canon(a) == _canon(b)


def _output(r: Run) -> dict | None:
    """The structured answer: root ``agentest.output`` (JSON object), else the answer text when it is a JSON object."""
    o = jattr(r.attrs, "agentest.output")
    if isinstance(o, dict):
        return o
    try:
        o = json.loads(r.answer) if (r.answer or "").strip()[:1] == "{" else None
    except ValueError:
        o = None
    return o if isinstance(o, dict) else None


# ---------------------------------------------------------------- NT-015 stepwise rationale (A029)

@rule("NT-015", what="Stepwise rationale: every high-impact call (approval targets or agentest.step.high_impact=true) carries agentest.step.rationale (or agentest.tool.reason) whose refs or values point to earlier recorded inputs or tool results.")
def _nt_015(c: Ctx, tid: str) -> R:
    targets = c.approval_targets()
    bad, n = [], 0
    for r in c.runs:
        for t in r.tools:
            if t.error or not (_true(tattr(t, "agentest.step.high_impact")) or t.name in targets):
                continue
            n += 1
            # the existing per-call reason fields (agentest.tool.reason, a 'reason' argument) count as free-text rationale
            rat = tattr(t, "agentest.step.rationale") or tattr(t, "agentest.tool.reason") or t.args.get("reason")
            where = f"{r.input_id}#{r.rep} {t.name}"
            if rat in (None, "", [], {}):
                bad.append(f"{where}: no rationale")
                continue
            vals, refs = _sources_before(r, t.t)
            if isinstance(rat, dict) and (rat.get("refs") or rat.get("values")):
                miss = [x for x in _list(rat.get("refs")) if str(x) not in refs]
                miss += [x for x in _list(rat.get("values")) if _canon(x) not in vals]
                if miss:
                    bad.append(f"{where}: rationale cites {miss[:3]} not recorded before the call")
                continue
            txt = _reason_text(rat) if isinstance(rat, dict) else _text(rat)
            earlier = [v for x in r.tools if x.t < t.t for v in _scalars(x.args) + _scalars(_result(x))]
            if not _mentions(txt, earlier + _scalars(r.input)):
                bad.append(f"{where}: rationale cites no earlier input or tool result")
    need(n, "no high-impact call (no approval target and no agentest.step.high_impact) in the traces")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{n} high-impact call(s) carry a grounded rationale")


# ---------------------------------------------------------------- NT-016 why probes (A031)

def _probe_target(r: Run, s: dict) -> ToolSpan | None:
    want = s["attrs"].get("agentest.probe.target")
    before = [t for t in r.tools if t.t <= s["t0"]]
    if want in (None, ""):
        return before[-1] if before else None
    hit = [t for t in r.tools if want in (t.call_id, t.name)]
    return hit[-1] if hit else None


@rule("NT-016", what="Why probes: each agentest.probe.kind=why span replies citing the target decision's recorded inputs or rule, within agentest.task.probe_latency_s when declared.")
def _nt_016(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for r in c.runs:
        limit = task(r, "probe_latency_s")
        for s in r.spans:
            a = s["attrs"]
            if str(a.get("agentest.probe.kind", "")).lower() != "why":
                continue
            n += 1
            where = f"{r.input_id}#{r.rep} probe {s.get('id') or s['name']}"
            tgt = _probe_target(r, s)
            if tgt is None:
                bad.append(f"{where}: target decision {a.get('agentest.probe.target') or '(none before the probe)'} not recorded")
                continue
            reply = a.get("agentest.probe.reply") or _text_of(a.get("gen_ai.output.messages") or "")
            cite = _scalars(tgt.args) + _scalars(tattr(tgt, "agentest.step.rule")) + _scalars(tattr(tgt, "agentest.step.rationale"))
            if not str(reply).strip():
                bad.append(f"{where}: no reply")
            elif not _mentions(str(reply), cite):
                bad.append(f"{where}: reply cites none of {tgt.name}'s recorded inputs or rule")
            if limit not in (None, ""):
                try:
                    lim = float(limit)
                except (TypeError, ValueError):
                    lim = None
                dur = (s["t1"] - s["t0"]) / 1e9
                if lim is not None and dur > lim:
                    bad.append(f"{where}: answered in {dur:.1f}s > {lim:g}s")
    need(n, "no agentest.probe.kind=why span in the traces")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{n} why probe(s) answered with the decision's inputs in time")


# ---------------------------------------------------------------- NT-017 structured knowledge lookups (A033)

def _is_lookup(t: ToolSpan, declared: list) -> bool:
    return str(tattr(t, "agentest.tool.kind", "")).lower() in ("knowledge_lookup", "knowledge") or t.name in declared


@rule("NT-017", what="Knowledge lookups: each output field in agentest.task.knowledge_fields equals a value from a knowledge-lookup tool result (agentest.tool.kind=knowledge_lookup or agentest.task.knowledge_tools); a missing lookup or a mismatch fails.")
def _nt_017(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for r in c.runs:
        fields = task(r, "knowledge_fields")
        if not fields:
            continue
        fields = list(fields) if isinstance(fields, (list, dict)) else [fields]
        n += 1
        where = f"{r.input_id}#{r.rep}"
        out = _output(r)
        if out is None:
            bad.append(f"{where}: no structured output (agentest.output or JSON answer)")
            continue
        declared = _list(task(r, "knowledge_tools"))
        res = [_result(t) for t in r.tools if not t.error and _is_lookup(t, declared)]
        if not res:
            bad.append(f"{where}: no successful knowledge lookup")
            continue
        for f in fields:
            v = _get(out, f)
            if v in (None, ""):
                bad.append(f"{where}: output lacks {f}")
                continue
            leaf = str(f).split(".")[-1]
            keyed = [x for y in res for x in _key_values(y, leaf)]
            pool = keyed or [x for y in res for x in _scalars(y)]
            if not all(x in pool for x in _scalars(v)):
                bad.append(f"{where}: {f}={v!r} not in the lookup result")
    need(n, "no run declares agentest.task.knowledge_fields")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{n} run(s): knowledge fields match the lookups")


# ---------------------------------------------------------------- decision records (NT-018, NT-019, NT-028, NT-029)

def _consequential(r: Run, d: dict) -> bool:
    if d.get("consequential") is not None:
        return _true(d.get("consequential"))
    outs = {_canon(x) for x in _list(task(r, "consequential_outcomes"))}
    return bool(outs) and _canon(d.get("outcome")) in outs


@rule("NT-018", what="Principal reasons: every consequential decision record (agentest.decision.consequential, or outcome in agentest.task.consequential_outcomes) lists reasons, each mapped to an input present in the record.")
def _nt_018(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for r in c.runs:
        for d in _decisions(r):
            if not _consequential(r, d):
                continue
            n += 1
            where = f"{r.input_id}#{r.rep} decision {d['id']}"
            inputs = d.get("inputs")
            reasons = _list(d.get("reasons"))
            if not reasons:
                bad.append(f"{where}: no reasons")
                continue
            if not isinstance(inputs, (dict, list)) or not inputs:
                bad.append(f"{where}: no inputs recorded")
                continue
            for x in reasons:
                g, why = _reason_grounded(x, _as_keys(inputs), _scalars(inputs))
                if not g:
                    bad.append(f"{where}: reason {why}")
    need(n, "no consequential decision record in the traces")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{n} consequential decision(s) carry grounded reasons")


def _notices(r: Run) -> list[dict]:
    out = []
    for s in r.spans:
        a = s["attrs"]
        n = jattr(a, "agentest.notice")
        if isinstance(n, dict):
            out.append(n)
        elif s["name"] == "agentest.notice":
            out.append({k[len("agentest.notice."):]: jattr(a, k) for k in a if k.startswith("agentest.notice.")})
    return out


@rule("NT-019", what="Decision notices: an agentest.notice has every section and field of agentest.task.notice_template, and each field value equals the decision record.")
def _nt_019(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for r in c.runs:
        tpl = task(r, "notice_template")
        decs = _decisions(r)
        if not isinstance(tpl, dict) or not decs:
            continue
        cons = [d for d in decs if _consequential(r, d)] or decs
        n += 1
        where = f"{r.input_id}#{r.rep}"
        notes = _notices(r)
        if not notes:
            bad.append(f"{where}: decision recorded but no notice")
            continue
        for note in notes:
            d = next((x for x in cons if str(x["id"]) == str(note.get("decision_id"))), cons[-1])
            have = _as_keys(note.get("sections"))
            miss = [s for s in _list(tpl.get("sections")) if str(s).lower() not in have]
            if miss:
                bad.append(f"{where}: notice lacks sections {miss}")
            fields = tpl.get("fields") or {}
            if isinstance(fields, list):
                fields = {f: f for f in fields}
            nf = note.get("fields") if isinstance(note.get("fields"), dict) else {}
            for f, src in fields.items():
                v = nf.get(f)
                if v in (None, ""):
                    bad.append(f"{where}: notice lacks field {f}")
                elif not _same(v, _get(d, src)):
                    bad.append(f"{where}: notice {f}={v!r} differs from decision {src}={_get(d, src)!r}")
    need(n, "no run declares agentest.task.notice_template with a decision record")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{n} run(s): notices match the template and the decision")


@rule("NT-028", what="Explanation records: every decision record has non-empty inputs, criteria, outcome and reasons, and every reason refers to a present input or criterion.")
def _nt_028(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for r in c.runs:
        for d in _decisions(r):
            n += 1
            where = f"{r.input_id}#{r.rep} decision {d['id']}"
            empty = [k for k in ("inputs", "criteria", "outcome", "reasons") if d.get(k) in (None, "", [], {})]
            if empty:
                bad.append(f"{where}: empty {empty}")
                continue
            keys = _as_keys(d["inputs"]) | _as_keys(d["criteria"])
            vals = _scalars(d["inputs"]) + _scalars(d["criteria"])
            for x in _list(d["reasons"]):
                g, why = _reason_grounded(x, keys, vals)
                if not g:
                    bad.append(f"{where}: reason {why}")
    need(n, "no decision record in the traces")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{n} decision record(s) reconstruct their explanation")


@rule("NT-029", what="Reviewer reconstruction: every output value of a sampled decision appears in a recorded input, tool result or rule, or has a declared derivation whose sources exist.")
def _nt_029(c: Ctx, tid: str) -> R:
    bad, n = [], 0
    for r in c.runs:
        decs = _decisions(r)
        sample = {str(x) for x in _list(task(r, "review_sample"))}
        flagged = [d for d in decs if _true(d.get("sampled")) or str(d["id"]) in sample]
        for d in flagged or ([] if sample else decs):
            n += 1
            where = f"{r.input_id}#{r.rep} decision {d['id']}"
            outs = d.get("outputs")
            if not isinstance(outs, dict) or not outs:
                outs = {"outcome": d.get("outcome")} if d.get("outcome") not in (None, "") else {}
            if not outs:
                bad.append(f"{where}: no outputs recorded")
                continue
            vals, refs = _sources_before(r, None)
            vals += _scalars(d.get("inputs")) + _scalars(d.get("criteria")) + _scalars(d.get("rule"))
            refs |= _as_keys(d.get("inputs")) | _as_keys(d.get("criteria"))
            der = d.get("derivations") if isinstance(d.get("derivations"), dict) else {}
            for f, v in outs.items():
                if f in der:
                    srcs = _list(der[f].get("sources") if isinstance(der[f], dict) else der[f])
                    miss = [s for s in srcs if str(s).lower() not in {x.lower() for x in refs}]
                    if not srcs or miss:
                        bad.append(f"{where}: {f} derivation sources {miss or '(none)'} not recorded")
                    continue
                texts = _text(d.get("rule")) + " " + (r.input or "")
                if not all(x in vals or _mentions(texts, [x]) for x in _scalars(v)):
                    bad.append(f"{where}: {f}={v!r} traces to no recorded input, tool result or rule")
    need(n, "no (sampled) decision record in the traces")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{n} sampled decision(s) reconstruct from the trace")
