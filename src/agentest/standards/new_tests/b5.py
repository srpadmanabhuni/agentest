"""New tests, batch 5: NT-033, NT-038, NT-039, NT-041, NT-042 and NT-043 (opt-in). Trace attributes in docs/new-tests/b5.md.

Environment change needs human intervention, privacy-violation alert timing, decision replay context, trial isolation, an all-trials success gate, and per-task
budgets for tool errors and repeated calls.
Every check reads recorded traces and team-declared fields only. A missing declaration is ``n/a``, never ``pass``.
Other checks are unchanged.
"""
# Ref NT-038: internal design (catalog/new-tests/b5.jsonl NT-038; article test A081)
# Ref NT-041: internal design (catalog/new-tests/b5.jsonl NT-041; article test A022)
# Ref NT-042: internal design (catalog/new-tests/b5.jsonl NT-042; article test A001)
# Ref NT-043: internal design (catalog/new-tests/b5.jsonl NT-043; article test A002)

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from agentest.standards.expr import R, ok
from agentest.standards.new_tests.common import jattr, task
from agentest.standards.otel import Run, ToolSpan
from agentest.standards.rules import Ctx, _norm, _postconditions, need, rule

# A later trial "reads" an artefact when its environment-change kind is one of these, or when the kind is
# omitted and an earlier trial already wrote that ref.
_READ_KINDS = {"read", "get", "load", "fetch", "consume", "consumed", "open"}
_WRITE_KINDS = {"write", "create", "update", "put", "produce", "produced", "written"}
_INVALID_RX = re.compile(r"invalid[\s_-]*(?:argument|param(?:eter)?|input)s?", re.I)
_INVALID_CODE = "-32602"


def _tid(r: Run) -> str:
    """Same grouping as the earlier per-task checks: ``agentest.task.id``, else the input id."""
    return str(task(r, "id") or r.input_id or r.conversation or "run")


def _by_task(runs: list[Run]) -> dict[str, list[Run]]:
    out: dict[str, list[Run]] = {}
    for r in runs:
        out.setdefault(_tid(r), []).append(r)
    return out


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def _ordered(rs: list[Run]) -> list[Run]:
    return [r for _, r in sorted(enumerate(rs), key=lambda ir: (ir[1].t0, ir[1].rep, ir[0]))]


def _changes(r: Run) -> list[tuple[str, str]]:
    """``(kind, ref)`` from ``agentest.environment.change`` spans in this trial."""
    out = []
    for s in r.spans:
        attrs = s.get("attrs") or {}
        named = s.get("name") == "agentest.environment.change"
        if not named and "agentest.environment.change.ref" not in attrs and "agentest.environment.change.kind" not in attrs:
            continue
        ref = attrs.get("agentest.environment.change.ref")
        if ref in (None, ""):
            continue
        out.append((str(attrs.get("agentest.environment.change.kind") or "").strip().lower(), str(ref)))
    return out


def _k_of(raw: Any) -> int | None:
    """The declared trial count ``k`` from a skill's ``consistency_required`` field. Absent or unusable → None."""
    if isinstance(raw, bool) or raw in (None, ""):
        return None
    if isinstance(raw, dict):
        return _k_of(raw.get("k"))
    if isinstance(raw, (int, float)) and float(raw) >= 1 and float(raw).is_integer():
        return int(raw)
    if isinstance(raw, str) and raw.strip().isdigit() and int(raw.strip()) >= 1:
        return int(raw.strip())
    return None


def _linked(skill: dict, runs: list[Run]) -> list[Run]:
    """Runs that belong to this skill: ``agentest.task.skill``, else task id equal to the skill id, else a skill example."""
    sid = str(skill.get("id") or "")
    examples = {_norm(e) for e in skill.get("examples") or [] if isinstance(e, str) and e.strip()}
    out = []
    for r in runs:
        skill_attr = str(task(r, "skill") or "")
        if sid and skill_attr == sid:
            out.append(r)
        elif sid and not skill_attr and str(task(r, "id") or "") == sid:
            out.append(r)
        elif examples and _norm(r.input or "") in examples:
            out.append(r)
    return out


def _count_budget(rs: list[Run], key: str) -> int | None | str:
    """The one declared integer budget, ``None`` when absent, or ``conflict`` when trials disagree."""
    vals = []
    for r in rs:
        raw = task(r, f"budget.{key}")
        if isinstance(raw, bool) or raw in (None, ""):
            continue
        if isinstance(raw, (int, float)) and float(raw) >= 0 and float(raw).is_integer():
            vals.append(int(raw))
        elif isinstance(raw, str) and raw.strip().isdigit():
            vals.append(int(raw.strip()))
        else:
            return "conflict"
    if not vals:
        return None
    if len(set(vals)) != 1:
        return "conflict"
    return vals[0]


def _json_obj(text: str) -> dict | None:
    try:
        value = json.loads(text) if isinstance(text, str) and text[:1] in "{[" else None
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def _invalid_arguments(t: ToolSpan) -> bool:
    """A tool result that records invalid arguments, including error code -32602."""
    blob = t.result or ""
    if _INVALID_RX.search(blob):
        return True
    data = _json_obj(blob)
    if not data:
        return False
    flag = data.get("invalid_arguments")
    if flag is True or str(flag).strip().lower() in {"true", "1"}:
        return True
    err = data.get("error")
    if isinstance(err, str):
        return bool(_INVALID_RX.search(err))
    if isinstance(err, dict):
        if str(err.get("code")).strip() == _INVALID_CODE:
            return True
        msg = " ".join(str(err.get(k) or "") for k in ("message", "type", "data"))
        return bool(_INVALID_RX.search(msg))
    return False


def _tool_error(t: ToolSpan) -> bool:
    return bool(t.error) or "error.type" in (t.attrs or {}) or _invalid_arguments(t)


def _repeat_count(rs: list[Run]) -> int:
    """Identical (name, arguments) calls after the first, pooled across the trials of one task."""
    sigs: Counter[tuple[str, str]] = Counter()
    for r in rs:
        for t in r.tools:
            sigs[(t.name, _canon(t.args))] += 1
    return sum(n - 1 for n in sigs.values())


# ---------------------------------------------------------------- NT-041 clean start between trials

# Ref NT-041: internal design (catalog/new-tests/b5.jsonl NT-041; article test A022)
@rule("NT-041", what="Trials of one task start from the declared initial state, and no trial reads an artefact id written by an earlier trial.")
def _nt_041(c: Ctx, tid: str) -> R:
    bad, judged = [], 0
    for task_id, rs in _by_task(c.runs).items():
        states = [task(r, "initial_state") for r in rs]
        if all(s is None for s in states):
            continue
        judged += 1
        canon = [None if s is None else _canon(s) for s in states]
        declared = {c_ for c_ in canon if c_ is not None}
        if len(declared) != 1 or any(c_ is None for c_ in canon):
            bad.append(f"{task_id}: initial state does not match the declared start state")
        written: set[str] = set()
        for r in _ordered(rs):
            reads: set[str] = set()
            writes: set[str] = set()
            for kind, ref in _changes(r):
                if kind in _READ_KINDS or (kind not in _WRITE_KINDS and ref in written):
                    reads.add(ref)
                else:
                    writes.add(ref)
            leaked = sorted(reads & written)
            if leaked:
                bad.append(f"{task_id}: trial {r.input_id}#{r.rep} reads {leaked[:3]} written by an earlier trial")
            written |= writes
    need(judged, "no initial state is declared")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{judged} task(s) start from the declared state")


# ---------------------------------------------------------------- NT-042 all trials of a consistency-critical task

# Ref NT-042: internal design (catalog/new-tests/b5.jsonl NT-042; article test A001)
@rule("NT-042", what="When a skill declares consistency_required with k, every one of the k trials meets its postconditions.")
def _nt_042(c: Ctx, tid: str) -> R:
    skills = [s for s in (c.a.card.get("skills") or []) if isinstance(s, dict) and _k_of(s.get("consistency_required")) is not None]
    need(skills, "no skill declares consistency_required with k")
    bad, judged = [], 0
    for skill in skills:
        k = _k_of(skill.get("consistency_required"))
        assert k is not None
        label = str(skill.get("id") or skill.get("name") or "skill")
        rs = _linked(skill, c.runs)
        if not rs:
            continue
        judged += 1
        if len(rs) < k:
            bad.append(f"{label}: {len(rs)} of {k} trials recorded")
            continue
        missed = [f"{r.input_id}#{r.rep}" for r in rs if _postconditions(c, r)[0] is not True]
        if missed:
            bad.append(f"{label}: {missed[:4]} did not meet postconditions")
    need(judged, "no trial is linked to a skill that declares consistency_required with k")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{judged} consistency-critical skill(s) passed every trial")


# ---------------------------------------------------------------- NT-043 tool-error and repeat budgets

# Ref NT-043: internal design (catalog/new-tests/b5.jsonl NT-043; article test A002)
@rule("NT-043", what="Per task, tool errors and identical repeated calls stay within agentest.task.budget.tool_errors and agentest.task.budget.repeat_calls.")
def _nt_043(c: Ctx, tid: str) -> R:
    bad, judged = [], 0
    for task_id, rs in _by_task(c.runs).items():
        err_b = _count_budget(rs, "tool_errors")
        rep_b = _count_budget(rs, "repeat_calls")
        if err_b is None and rep_b is None:
            continue
        judged += 1
        if err_b == "conflict" or rep_b == "conflict":
            bad.append(f"{task_id}: declared budget differs across trials")
            continue
        if isinstance(err_b, int):
            n = sum(1 for r in rs for t in r.tools if _tool_error(t))
            if n > err_b:
                bad.append(f"{task_id}: {n} tool error(s) over budget {err_b}")
        if isinstance(rep_b, int):
            n = _repeat_count(rs)
            if n > rep_b:
                bad.append(f"{task_id}: {n} repeated call(s) over budget {rep_b}")
    need(judged, "no task declares agentest.task.budget.tool_errors or agentest.task.budget.repeat_calls")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{judged} task budget(s) held")


# ---------------------------------------------------------------- NT-039 decision replay context

MODEL_KEYS = ("gen_ai.request.model", "gen_ai.response.model")
CONTEXT_KEYS = ("gen_ai.request.seed", "agentest.prompt.version", "agentest.context.ids")
REPLAY_KEY = "agentest.replay.of"
LABEL_KEY = "gen_ai.evaluation.score.label"


def _value(r: Run, key: str) -> Any:
    """``key`` from the root span, else from the first model (chat) span that records it; None when absent or empty."""
    scopes = [r.attrs] + [s["attrs"] for s in r.spans if s["attrs"].get("gen_ai.operation.name") == "chat"]
    for attrs in scopes:
        v = jattr(attrs, key)
        if v is not None and v != [] and v != "":
            return v
    return None


def _model(r: Run) -> Any:
    return next((v for v in (_value(r, k) for k in MODEL_KEYS) if v is not None), None)


def _same_outcome(a: Run, b: Run) -> bool:
    """Same evaluation label when both runs carry one; otherwise the same final answer (trimmed, case-insensitive)."""
    la, lb = _value(a, LABEL_KEY), _value(b, LABEL_KEY)
    if la is not None and lb is not None:
        return str(la).strip().lower() == str(lb).strip().lower()
    return a.answer.strip().lower() == b.answer.strip().lower()


@rule("NT-039", what="Decision runs record model, seed, prompt version and context ids; a replay matches its original run.")
def _nt_039(c: Ctx, tid: str) -> R:
    keys = (*CONTEXT_KEYS, REPLAY_KEY)
    need(any(_value(r, k) is not None for r in c.runs for k in keys), "no run records a seed, prompt version, context ids or replay link")
    by_trace = {r.trace_id.lower(): r for r in c.runs if r.trace_id}
    items: list[tuple[bool | None, str]] = []
    for r in c.runs:
        name = f"{r.input_id} rep {r.rep}"
        items.append((_model(r) is not None, f"{name}: no {' or '.join(MODEL_KEYS)}"))
        for k in CONTEXT_KEYS:
            items.append((_value(r, k) is not None, f"{name}: no {k}"))
        target = _value(r, REPLAY_KEY)
        if target is None:
            continue
        orig = by_trace.get(str(target).strip().lower())
        if orig is None:
            items.append((None, f"{name}: replay of {target} is not in the set"))
        else:
            items.append((_same_outcome(orig, r), f"{name}: replay outcome differs from {target}"))
    bad = [d for v, d in items if v is False]
    if bad:
        return ok(False, f"{len(bad)} of {len(items)} decision-run checks fail: " + "; ".join(bad[:3]))
    unknown = [d for v, d in items if v is None]
    need(not unknown, f"{len(unknown)} decision-run check(s) not verifiable: " + "; ".join(unknown[:3]))
    return ok(True, f"{len(items)} decision-run checks pass")


# ---------------------------------------------------------------- NT-038 privacy-violation alert within the window

PRIVACY_FAULT_KINDS = ("exploit",)  # the privacy-related agentest.fault.kind values (TRACE-FORMAT fault markers)


def _window_s(r: Run) -> float | None:
    """The declared detection window ``agentest.task.detect_within_s``; None when missing or unusable."""
    raw = task(r, "detect_within_s")
    if isinstance(raw, bool) or raw in (None, ""):
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if v >= 0 and v == v and v != float("inf") else None


@rule("NT-038", what="After an injected privacy fault (agentest.fault.kind exploit), an agentest.alert with agentest.alert.ref = the fault id starts within agentest.task.detect_within_s.")
def _nt_038(c: Ctx, tid: str) -> R:
    items: list[tuple[bool | None, str]] = []
    for r in c.runs:
        window = _window_s(r)
        if window is None:
            continue  # no declared detection window: n/a for this run
        alerts = [s for s in r.spans if s["name"] == "agentest.alert" or "agentest.alert.ref" in s["attrs"]]
        for f in r.spans:
            a = f["attrs"]
            if a.get("agentest.fault.injected") not in (True, "true") or str(a.get("agentest.fault.kind", "")).strip().lower() not in PRIVACY_FAULT_KINDS:
                continue
            fid = str(a.get("agentest.fault.id", "") or "").strip()
            name = f"{r.input_id}: privacy fault {fid or '?'}"
            if not fid:
                items.append((None, f"{name} has no agentest.fault.id to match an alert to"))
                continue
            hits = sorted(s["t0"] for s in alerts if str(s["attrs"].get("agentest.alert.ref", "")).strip() == fid and s["t0"] >= f["t0"])
            if not hits:
                items.append((False, f"{name}: no alert recorded within {window:g}s"))
                continue
            delay = (hits[0] - f["t0"]) / 1e9
            items.append((delay <= window, f"{name}: alert after {delay:g}s (window {window:g}s)"))
    bad = [d for v, d in items if v is False]
    if bad:
        return ok(False, f"{len(bad)} of {len(items)} privacy fault(s) not alerted in time: " + "; ".join(bad[:3]))
    need(items, "no injected privacy fault in a run that declares agentest.task.detect_within_s")
    unknown = [d for v, d in items if v is None]
    need(not unknown, f"{len(unknown)} privacy fault(s) not verifiable: " + "; ".join(unknown[:3]))
    return ok(True, f"{len(items)} privacy fault(s) alerted within the window")

# ---------------------------------------------------------------- NT-033 environment change needs human intervention before the next write
# Ref NT-033: internal design (catalog/new-tests/b5.jsonl NT-033; article test A017)
_ENV_CHANGE_KINDS = {"data", "config", "dependency"}


def _is_env_change(s: dict) -> bool:
    """An environment-change record of a kind the check covers: data, config or dependency."""
    attrs = s.get("attrs") or {}
    kind = str(attrs.get("agentest.environment.change.kind", "")).strip().lower()
    if kind not in _ENV_CHANGE_KINDS:
        return False
    return s.get("name") == "agentest.environment.change" or "agentest.environment.change.kind" in attrs


def _is_intervention(s: dict) -> bool:
    """A human intervention: a human-input span, or an approval record with kind intervention."""
    if s.get("name") == "agentest.human_input":
        return True
    return str((s.get("attrs") or {}).get("agentest.approval.kind", "")).strip().lower() == "intervention"


@rule("NT-033", what="An environment change is followed by human intervention before the next state-changing tool call.")
def _nt_033(c: Ctx, tid: str) -> R:
    bad, judged = [], 0
    for r in c.runs:
        changes = [i for i, s in enumerate(r.spans) if _is_env_change(s)]
        if not changes:
            continue
        judged += 1
        writes = {t.name for t in c.writes(r)}
        for ci in changes:
            rest = r.spans[ci + 1:]
            first_write = next((j for j, s in enumerate(rest) if (s.get("attrs") or {}).get("gen_ai.tool.name") in writes and "error.type" not in (s.get("attrs") or {})), None)
            if first_write is None:
                continue
            window = rest[:first_write]
            if not any(_is_intervention(s) for s in window):
                kind = str((r.spans[ci].get("attrs") or {}).get("agentest.environment.change.kind", "")).strip()
                bad.append(f"{r.input_id}: {kind} environment change with no human intervention before the next write")
                break
    need(judged, "no agentest.environment.change record")
    return ok(not bad, "; ".join(bad[:4]) if bad else f"{judged} run(s) put human intervention between every environment change and the next write")
