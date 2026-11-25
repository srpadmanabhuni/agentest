"""Published postconditions: the expected end state an agent declares in its AgentCard governance extension.

One place for the operator table, the lookup order (``byExample`` -> ``byInput`` -> ``default``), the structural
lint that ``agentest std validate`` runs, and the per-run view that ``agentest std postconditions`` prints, so the
rules (T1-001, T1-002, T1-003, T1-018), the validator and the explainer cannot disagree about what a criterion means.
"""
# Ref: internal design (docs/standards/EXTENSION.md, postconditions); schema: schemas/governance-extension.schema.json.

from __future__ import annotations

import json
import re
from typing import Any

from agentest.standards.expr import get_path


def _dumps(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, default=str)


def _num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


OPS = {
    "eq": lambda v, w: v == w, "ne": lambda v, w: v != w, "nonempty": lambda v, w: bool(v), "truthy": lambda v, w: bool(v),
    "empty": lambda v, w: not v, "falsy": lambda v, w: not v,
    "contains": lambda v, w: str(w).lower() in _dumps(v).lower(), "excludes": lambda v, w: str(w).lower() not in _dumps(v).lower(),
    "le": lambda v, w: isinstance(v, (int, float)) and v <= w, "ge": lambda v, w: isinstance(v, (int, float)) and v >= w,
}
VALUE_OPS = ("eq", "ne", "contains", "excludes", "le", "ge")  # need "value"; the others ignore it
KEYS = ("default", "byInput", "byExample")


def norm(s: Any) -> str:
    """Input text as byExample matches it: lower-case letters and digits only."""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def criterion_problem(cr: Any) -> str | None:
    """Why a published criterion cannot be evaluated, or None when it is well formed."""
    if not isinstance(cr, dict):
        return f"criterion must be an object, got {type(cr).__name__}"
    path = cr.get("path")
    if not isinstance(path, str) or not path.strip():
        return "criterion needs a non-empty string 'path'"
    op = cr.get("op", "eq")
    if op not in OPS:
        return f"{path}: unknown op {op!r} (one of {', '.join(OPS)})"
    if op in VALUE_OPS and "value" not in cr:
        return f"{path}: op {op!r} needs a 'value'"
    if op in ("le", "ge") and not _num(cr.get("value")):
        return f"{path}: op {op!r} needs a numeric 'value', got {cr.get('value')!r}"
    return None


def lint(pc: Any) -> list[str]:
    """Structural problems in a published ``postconditions`` object, each one a short sentence.

    Catches what the runtime would otherwise crash on (unknown op, missing path) and what it would silently ignore
    (a misspelt top-level key, a byExample entry shadowed by an earlier one with the same normalised text)."""
    if pc is None:
        return []
    if not isinstance(pc, dict):
        return [f"postconditions must be an object, got {type(pc).__name__}"]
    errs = [f"postconditions: unknown key {k!r} (one of {', '.join(KEYS)}); it is ignored" for k in pc if k not in KEYS]

    def crits(where: str, xs: Any) -> None:
        if not isinstance(xs, list):
            errs.append(f"postconditions.{where} must be a list of criteria")
            return
        errs.extend(f"postconditions.{where}[{i}]: {p}" for i, cr in enumerate(xs) if (p := criterion_problem(cr)))

    if "default" in pc:
        crits("default", pc["default"])
    by_input = pc.get("byInput")
    if by_input is not None:
        if isinstance(by_input, dict):
            for k, xs in by_input.items():
                crits(f"byInput.{k}", xs)
        else:
            errs.append("postconditions.byInput must be an object of input id -> criteria")
    by_ex = pc.get("byExample")
    if by_ex is not None:
        if not isinstance(by_ex, list):
            errs.append("postconditions.byExample must be a list of {example, criteria}")
            by_ex = []
        seen: dict[str, int] = {}
        for i, e in enumerate(by_ex):
            if not isinstance(e, dict) or not isinstance(e.get("example"), str) or not e["example"].strip():
                errs.append(f"postconditions.byExample[{i}]: needs a non-empty string 'example'")
                continue
            if "criteria" not in e:
                errs.append(f"postconditions.byExample[{i}]: needs 'criteria'")
            else:
                crits(f"byExample[{i}].criteria", e["criteria"])
            k = norm(e["example"])
            if not k:
                errs.append(f"postconditions.byExample[{i}]: example has no letters or digits, so it matches no input")
            elif k in seen:
                errs.append(f"postconditions.byExample[{i}]: same example as byExample[{seen[k]}]; only the first is used")
            else:
                seen[k] = i
    return errs


def select(pc: dict, text: str, input_id: str) -> tuple[str, list]:
    """Which published criteria apply to one recorded input, and where they came from.

    Source is ``byExample[i]``, ``byInput.<id>``, ``default`` or ``none``. Same lookup order the rules use."""
    pc = pc if isinstance(pc, dict) else {}
    want = norm(text)
    for i, e in enumerate(pc.get("byExample") or []):
        if isinstance(e, dict) and norm(e.get("example", "")) == want:
            return f"byExample[{i}]", e.get("criteria") or []
    by_input = pc.get("byInput") or {}
    if isinstance(by_input, dict) and input_id in by_input:
        return f"byInput.{input_id}", by_input[input_id] or []
    return ("default", pc.get("default") or []) if pc.get("default") else ("none", [])


def check(cr: dict, state: dict) -> tuple[bool, Any]:
    """(holds, observed value) for one well-formed criterion against a recorded end state."""
    v = get_path(state, cr["path"])
    return bool(OPS[cr.get("op", "eq")](v, cr.get("value"))), v


def describe(cr: dict) -> str:
    """``path op value`` as the rules print it in an ``unmet:`` detail."""
    want = cr.get("value")
    return f"{cr['path']} {cr.get('op', 'eq')} {want if want is not None else ''}".strip()


def explain(agent, runs: list, mode: str = "examples") -> dict:
    """Per-run view of how the published postconditions judged each recorded run.

    For each run: where its criteria came from, each criterion's observed value and result, the success signal the
    T1 rules read, and whether the reply claims success (a claim with an unmet end state is what T1-002 / T1-018
    flag). Also lists byExample entries no recorded input reached, so a rule that is never exercised is visible."""
    from agentest.standards.rules import _claims_success  # rules imports this module; import late

    pc = agent.g("postconditions", default=None)
    problems = lint(pc)
    rows, used = [], set()
    for r in runs:
        row: dict[str, Any] = {"input_id": r.input_id, "rep": r.rep, "input": r.input, "claims_success": _claims_success(r.answer)}
        if r.error:
            row.update(source="run error", criteria=[], signal="fail", detail=f"error: {r.error[:80]}")
        elif r.evaluations:
            bad = any(str(e.get("gen_ai.evaluation.score.label", "")).lower() in ("fail", "incorrect") for e in r.evaluations)
            row.update(source="gen_ai.evaluation.result", criteria=[], signal="fail" if bad else "pass",
                       detail="evaluation events take precedence; published postconditions are not read")
        elif mode != "examples":
            row.update(source="strict mode", criteria=[], signal="none", detail="published postconditions are ignored in strict mode")
        else:
            src, crit = select(pc or {}, r.input, r.input_id)
            if src.startswith("byExample["):
                used.add(int(src[len("byExample["):-1]))
            out = []
            for cr in crit if isinstance(crit, list) else []:
                if (p := criterion_problem(cr)):
                    out.append({"criterion": cr, "problem": p})
                    continue
                held, v = check(cr, r.final_state)
                out.append({"criterion": describe(cr), "observed": v, "holds": held})
            if not out:
                sig, det = "none", "agent publishes no postconditions for this input"
            elif any("problem" in c for c in out):
                sig, det = "invalid", "a criterion is malformed; fix it (agentest std validate)"
            else:
                sig = "pass" if all(c["holds"] for c in out) else "fail"
                det = "postconditions hold" if sig == "pass" else "unmet: " + "; ".join(c["criterion"] for c in out if not c["holds"])
            row.update(source=src, criteria=out, signal=sig, detail=det)
        row["false_completion"] = bool(row["claims_success"] and row["signal"] == "fail")
        rows.append(row)
    examples = [e for e in (pc or {}).get("byExample") or []] if isinstance(pc, dict) else []
    unused = [{"index": i, "example": e.get("example")} for i, e in enumerate(examples)
              if isinstance(e, dict) and i not in used and norm(e.get("example", ""))]
    counts: dict[str, int] = {}
    for row in rows:
        k = row["source"].split("[")[0].split(".")[0]
        counts[k] = counts.get(k, 0) + 1
    return {"mode": mode, "problems": problems, "runs": rows, "sources": counts, "unused_examples": unused}
