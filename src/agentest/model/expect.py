"""Profile expectations: catalogue checks written as data, evaluated over standard traces.

A profile (or a shared library it ``extends``) may state, per catalogue ID, an
*expectation*: a side-effect-free expression in the safe language of
:mod:`agentest.model.expr`. The expression sees only

* ``E`` - the agent's episodes (standard traces) for this run, with
  ``E.all``, ``E.by``, ``E.get(probe)`` (all reps), ``E.one(probe)`` (first rep,
  raises on a recorded error) and ``E.out(probe)`` (its final output dict);
  each episode is a read-only dict view ``{agent, probe, rep, input, output,
  extra, trace, error, elapsed_s}`` built from the standard
  :class:`~agentest.model.trace.Episode` (``trace`` = native span events);
* ``P`` - the profile (tools, limits, probes, ...);
* the profile's ``defs`` and the library in :data:`agentest.model.expr.FUNCS`.

It evaluates to a verdict (``ok(cond, detail)`` / ``R(status, detail)`` / a bool)
or to a callable that is then called with ``E``. ``applies`` gives an optional
applicability expression per ID (false -> ``n/a``). The engine is the same for
every agent; nothing here names an agent or a scenario.
"""

from __future__ import annotations

from typing import Any

from agentest.model.expr import R, bind, evaluate, wrap
from agentest.model.profile import Profile
from agentest.model.trace import Episode

_FAIL_ON = (KeyError, RuntimeError, IndexError, TypeError, AttributeError, ValueError)


class Eps:
    """Episodes of one agent indexed by probe."""

    def __init__(self, eps: list[dict]) -> None:
        self.all = eps
        self.by: dict[str, list[dict]] = {}
        for e in eps:
            self.by.setdefault(e["probe"], []).append(e)

    def get(self, probe: str) -> list[dict]:
        if probe not in self.by:
            raise KeyError(f"probe {probe!r} not recorded")
        return self.by[probe]

    def one(self, probe: str) -> dict:
        e = self.get(probe)[0]
        if e.get("error"):
            raise RuntimeError(f"{probe}: {e['error'][:160]}")
        return e

    def out(self, probe: str) -> dict:
        return self.one(probe)["output"] or {}

    def has(self, probe: str) -> bool:
        return probe in self.by


def view(ep: Episode) -> dict:
    """Read-only dict view of a standard episode for expressions."""
    fs = ep.final_state or {}
    return wrap({"agent": ep.agent, "probe": ep.probe, "rep": ep.rep, "input": fs.get("input", ep.input),
                 "output": fs.get("output"), "extra": fs.get("extra") or {}, "trace": list(ep.events or []),
                 "error": ep.error, "elapsed_s": ep.duration_s, "final_answer": ep.final_answer,
                 "tool_calls": [{"name": c.name, "arguments": c.arguments, "result": c.result, "actor": c.actor,
                                 "side_effect": c.side_effect, "error": c.error} for c in ep.tool_calls]})


def _verdict(v: Any) -> R:
    if isinstance(v, R):
        return v
    if isinstance(v, bool):
        return R("pass" if v else "fail", "")
    if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str):
        return R(v[0], str(v[1]))
    raise TypeError(f"expectation must give ok(...)/R(...)/bool, got {type(v).__name__}")


def evaluate_expectations(prof: Profile, eps: list[Episode], ids: list[str] | None = None) -> dict[str, R]:
    """Evaluate the profile's ``expect`` entries; IDs without one are omitted."""
    if not prof.expect:
        return {}
    E = Eps([view(e) for e in eps])
    g = bind(prof.defs or {}, {"P": prof, "E": E})
    out: dict[str, R] = {}
    for tid, src in prof.expect.items():
        if ids is not None and tid not in ids:
            continue
        if not eps:
            out[tid] = R("not-run", "no recorded episodes")
            continue
        try:
            cond = prof.applies.get(tid)
            if cond is not None and not evaluate(str(cond), g):
                out[tid] = R("n/a", f"profile: not applicable ({str(cond)[:80]})")
                continue
            v = evaluate(str(src), g)
            if callable(v) and not isinstance(v, R):
                v = v(E)
            out[tid] = _verdict(v)
        except _FAIL_ON as ex:
            out[tid] = R("fail", f"{type(ex).__name__}: {ex}")
    return out
