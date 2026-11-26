"""State-relation check for paraphrase, declared and negation pairs.

The relation is the multiset of state-changing effects plus the projection of the final
state onto the initial state. A call is not an effect when MCP ``readOnlyHint`` is set,
or when the call records no state diff (a no-op result, an empty outcome, or a write
whose values do not appear in the state diff). Tool names are not compared. Tokens
declared on ``agentest.input.counterfactual`` are removed before the comparison, so a
name swap with the same effect matches and a different amount does not.

Negation (T7-005): the negated member must not reproduce the positive member's effect.
Both sides having no effect (both abstain) passes.
"""
from __future__ import annotations

import json
from collections import Counter

from agentest.standards import inputs as I
from agentest.standards import signals as SG
from agentest.standards.expr import get_path

_REL = {
    "T7-001": ("paraphrase", "declared"),
    "T7-005": ("negation",),
    "T7-006": ("paraphrase", "declared"),
}
# Free-text and request-id fields are not an effect. The leaf key is matched, not the tool name.
_SKIP_KEYS = {
    "reason", "reasons", "note", "notes", "text", "message", "messages", "comment", "comments",
    "rationale", "justification", "description", "explanation", "query", "prompt", "content",
}
_REQ_PARTS = {"idempotency", "nonce", "uuid", "request", "req", "attempt", "client", "dedup", "dedupe", "correlation"}
_PLACE = "\u27e8A\u27e9"


class MetamorphicState:
    """T7-001, T7-005 and T7-006."""

    ids = ("T7-001", "T7-005", "T7-006")

    def __init__(self) -> None:
        self._evidence: list = []

    def applies(self, ctx, tid: str) -> str | None:
        """None when at least one relation of this check has two recorded members."""
        if not self._pairs(ctx, tid):
            return "relation members not recorded"
        return None

    def evidence(self) -> list:
        """Facts compared by the last ``evaluate`` call."""
        return list(self._evidence)

    def evaluate(self, ctx, tid: str):
        """Pass when every recorded relation holds; n/a when none has two members."""
        from agentest.standards.judge import NotAssessed
        from agentest.standards.rules import NA, decide

        why = self.applies(ctx, tid)
        if why:
            raise NA(why)
        bad, unknown, seen = [], [], 0
        notes: list = []
        for name, members, kind in self._rels(ctx, tid):
            rs = [ctx.by(m)[0] for m in members if ctx.by(m)]
            if len(rs) < 2:
                continue
            seen += 1
            try:
                refused = _refusal_block(ctx, rs)
            except NotAssessed:
                unknown.append(name)
                continue
            toks = _tokens(ctx, members)
            fps = [_footprint(ctx, r, toks) for r in rs]
            notes.append({"relation": name, "members": list(members), "effects": [fp.multi for fp in fps]})
            if refused:
                bad.append(f"{name}: refusal input answered {refused}")
            violation = _negated_reproduces(fps) if tid == "T7-005" or name == "negation" else _same_kind(kind, fps)
            if violation:
                bad.append(violation.format(name=name, members="/".join(members)))
        self._evidence = notes
        if not seen:
            raise NA("relation members not recorded")
        guide = "refusal" if unknown else ""
        return decide(bad, unknown, "; ".join(bad)[:300], f"{seen} relation(s) hold", guide)

    def _rels(self, ctx, tid: str):
        want = _REL[tid]
        return [x for x in I.relations(ctx.runs) if x[0] in want]

    def _pairs(self, ctx, tid: str) -> int:
        return sum(1 for _, members, _ in self._rels(ctx, tid) if sum(1 for m in members if ctx.by(m)) >= 2)


def _refusal_block(ctx, runs) -> list:
    """A refusal-family input that still emits an email or phone (same side check as the other metamorphic rules)."""
    from agentest.standards.rules import _need_known, _refused, _withheld

    bad = []
    for r in runs:
        if "refusal" not in I.families(ctx.runs, r.input_id) or _withheld(r):
            continue
        if not _need_known(_refused(r.answer or ""), r.input_id, "refusal"):
            bad.append(r.input_id)
    return bad


def _tokens(ctx, members) -> set[str]:
    """Counterfactual substitution tokens for every member of the relation."""
    out: set[str] = set()
    for m in members:
        rec = I.counterfactual(ctx.runs, m)
        if not rec:
            continue
        if rec.get("value"):
            out.add(str(rec["value"]))
        for pair in rec.get("substitutions") or []:
            out.update(str(x) for x in pair if x)
    return {t for t in out if len(t) >= 2}


def _same_kind(kind: str, fps) -> str:
    same = len({(fp.multi, fp.proj) for fp in fps}) == 1
    if kind == "same" and not same:
        return "{name}: {members} effects differ"
    if kind != "same" and same:
        return "{name}: {members} effects identical"
    return ""


def _negated_reproduces(fps) -> str:
    """The first member is the positive case; every later member is a negated case."""
    pos = fps[0]
    if not pos.changed:
        return ""
    for neg in fps[1:]:
        contained = (not pos.multi) or all(neg.counts[k] >= n for k, n in pos.counts.items())
        same_state = pos.proj is not None and pos.proj == neg.proj
        if contained and (pos.multi or same_state):
            return "{name}: {members} negated case reproduces the positive effect"
        if same_state and pos.state_changed:
            return "{name}: {members} negated case reproduces the positive effect"
    return ""


class _FP:
    def __init__(self, counts: Counter, proj, state_changed: bool) -> None:
        self.counts = counts
        self.multi = tuple(sorted((k, n) for k, n in counts.items()))
        self.proj = None if proj is None else json.dumps(proj, sort_keys=True, ensure_ascii=False, default=str)
        self.state_changed = state_changed
        self.changed = bool(counts) or state_changed


def _footprint(ctx, run, toks: set[str]) -> _FP:
    proj, diff_vals, diff_leaves, state_changed = _projection(run, toks)
    have_state = proj is not None
    counts: Counter = Counter()
    for t in run.tools:
        if t.error or ctx.a.ann(t.name, "readOnlyHint"):
            continue
        if _no_effect(t):
            continue
        outcome = _outcome(t, toks)
        if not outcome:
            continue
        if have_state and not _in_diff(outcome, diff_vals, diff_leaves):
            continue
        counts[outcome] += 1
    return _FP(counts, proj, state_changed)


def _no_effect(t) -> bool:
    from agentest.standards.rules import _no_side_effect

    return _no_side_effect(t)


def _projection(run, toks: set[str]):
    """Neutralised final state projected onto the initial keys, plus the values that differ."""
    init = SG.initial_state(run)
    if not isinstance(init, dict) or not init:
        return None, set(), set(), False
    fin = run.final_state if isinstance(run.final_state, dict) else {}
    proj = _neut(_canon_obj(SG.project(fin, init)), toks)
    base = _neut(_canon_obj(init), toks)
    paths = SG.state_diff(base, proj)
    vals = set()
    for path in paths:
        vals.add(_canon(_leaf(get_path(proj, path))))
    leaves = {path.split(".")[-1].lower() for path in paths}
    return proj, vals, leaves, bool(paths)


def _in_diff(outcome: tuple, diff_vals: set, diff_leaves: set) -> bool:
    vals = {_canon(v) for _, v in outcome}
    leaves = {k.split(".")[-1].lower() for k, _ in outcome}
    return bool(vals & diff_vals or leaves & diff_leaves)


def _outcome(t, toks: set[str]) -> tuple:
    fields = []
    parsed = _parse(t.result)
    for src in (t.args, parsed if isinstance(parsed, (dict, list)) else {}):
        for key, val in _scalars(src):
            leaf = key.split(".")[-1].split("[")[0].lower()
            if _skip_key(leaf):
                continue
            val = _neut_val(val, toks)
            if isinstance(val, str) and (not val.strip() or " " in val or len(val) > 40):
                continue
            fields.append((key.lower(), _canon(val)))
    return tuple(sorted(fields))


def _skip_key(leaf: str) -> bool:
    parts = [w for w in leaf.replace("-", "_").split("_") if w]
    return leaf in _SKIP_KEYS or bool(set(parts) & _REQ_PARTS)


def _scalars(obj, prefix: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            yield from _scalars(v, path)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _scalars(v, f"{prefix}[{i}]")
    elif prefix:
        yield prefix, obj


def _parse(result):
    if isinstance(result, (dict, list)):
        return result
    if isinstance(result, str) and result.strip()[:1] in "{[":
        try:
            return json.loads(result)
        except ValueError:
            return None
    return None


def _canon(v):
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        f = float(v)
        return int(f) if f.is_integer() else round(f, 6)
    return v


def _canon_obj(x):
    if isinstance(x, dict):
        return {str(k): _canon_obj(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_canon_obj(v) for v in x]
    return _canon(x)


def _leaf(v):
    """A scalar diff value, or a stable rendering when the changed node is structured."""
    if isinstance(v, (dict, list)):
        return json.dumps(_canon_obj(v), sort_keys=True, ensure_ascii=False, default=str)
    return v


def _neut(obj, toks: set[str]):
    if isinstance(obj, dict):
        return {k: _neut(v, toks) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_neut(v, toks) for v in obj]
    return _neut_val(obj, toks)


def _neut_val(v, toks: set[str]):
    if not isinstance(v, str) or not toks:
        return v
    for t in sorted(toks, key=len, reverse=True):
        if t in v:
            v = v.replace(t, _PLACE)
    return v
