"""Test-owned conformance-scenario oracles (``scenarios.yaml``), keyed by catalogue ID only.

A scenario oracle judges a run whose input id IS the catalogue id (the agentest conformance harness records such
runs). It is a side-effect-free expression in the safe language of :mod:`agentest.standards.expr` and sees only

* ``E`` - those runs, with ``E.all``, ``E.by``, ``E.get(id)``, ``E.one(id)`` (first rep, raises on a recorded error)
  and ``E.out(id)`` (its final output dict, from the OTLP root attribute ``agentest.final_state``);
* the ``defs`` of ``scenarios.yaml`` and the functions in :data:`agentest.standards.expr.FUNCS`.

Nothing here names an agent.
"""

from __future__ import annotations

from typing import Any

from agentest.standards.expr import R, bind, evaluate, wrap

_FAIL_ON = (KeyError, RuntimeError, IndexError, TypeError, AttributeError, ValueError)


class Eps:
    """Runs indexed by input id."""

    def __init__(self, eps: list[dict]) -> None:
        self.all = eps
        self.by: dict[str, list[dict]] = {}
        for e in eps:
            self.by.setdefault(e["probe"], []).append(e)

    def get(self, probe: str) -> list[dict]:
        if probe not in self.by:
            raise KeyError(f"input {probe!r} not recorded")
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


def view(run, is_write) -> dict:
    """Read-only dict view of one OTLP run for expressions."""
    fs = run.final_state or {}
    return wrap({"probe": run.input_id, "rep": run.rep, "input": fs.get("input", run.input), "output": fs.get("output"),
                 "extra": fs.get("extra") or {}, "error": run.error or None, "elapsed_s": run.duration_s, "final_answer": run.answer,
                 "tool_calls": [{"name": t.name, "arguments": t.args, "result": t.result, "actor": t.actor,
                                 "side_effect": "write" if is_write(t.name) else "read", "error": t.error} for t in run.tools]})


def _verdict(v: Any) -> R:
    if isinstance(v, R):
        return v
    if isinstance(v, bool):
        return R("pass" if v else "fail", "")
    if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str):
        return R(v[0], str(v[1]))
    raise TypeError(f"expectation must give ok(...)/R(...)/bool, got {type(v).__name__}")


def evaluate_expectations(expect: dict[str, str], defs: dict, views: list[dict], applies: dict | None = None) -> dict[str, R]:
    E = Eps(views)
    g = bind(defs or {}, {"E": E})
    out: dict[str, R] = {}
    for tid, src in expect.items():
        if not views:
            out[tid] = R("not-run", "no recorded runs")
            continue
        try:
            cond = (applies or {}).get(tid)
            if cond is not None and not evaluate(str(cond), g):
                out[tid] = R("n/a", f"scenario: not applicable ({str(cond)[:80]})")
                continue
            v = evaluate(str(src), g)
            if callable(v) and not isinstance(v, R):
                v = v(E)
            out[tid] = _verdict(v)
        except _FAIL_ON as ex:
            out[tid] = R("fail", f"{type(ex).__name__}: {ex}")
    return out
