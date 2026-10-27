"""Instrumentation-coverage gate (v3.5).

A verdict of ``n/a`` means a rule found no standard signal in the traces or metadata. A few n/a cells are normal (an
agent that never asks for approval has nothing for the approval rules to read); a very high share usually means the
traces carry too little OpenTelemetry GenAI instrumentation for the checks to say anything. The gate fails an agent
whose share of uncovered cells (``n/a`` plus ``not-run``) is above a threshold, so a silent, uninstrumented build
cannot pass by default.

* share = uncovered / considered, where IDs disabled by config are left out of both counts;
* ``not-assessed`` (no judge configured) is a judge-coverage question, not an instrumentation one: it is reported
  apart and never counted as uncovered;
* default threshold :data:`DEFAULT_MAX_NA` (0.90). Override with ``--max-na`` or ``thresholds: max_na_share`` in the
  config file; ``1`` turns the gate off.

The report also lists which standard trace signals were seen (tool spans, model calls, token usage, agent names,
state-change events ...), so a failing agent shows what to instrument next. Nothing here names an agent.
"""

from __future__ import annotations

DEFAULT_MAX_NA = 0.90
RULE_ID = "agentest/instrumentation-coverage"

# signal -> (description, test over a Run)
SIGNALS: dict[str, tuple[str, object]] = {
    "tool_spans": ("execute_tool spans (gen_ai.tool.name)", lambda r: bool(r.tools)),
    "tool_arguments": ("tool call arguments (gen_ai.tool.call.arguments)", lambda r: any(t.args for t in r.tools)),
    "tool_results": ("tool call results (gen_ai.tool.call.result)", lambda r: any(t.result for t in r.tools)),
    "model_calls": ("chat / text_completion spans", lambda r: bool(r.chats) or bool(r.usage)),
    "token_usage": ("gen_ai.usage.input_tokens / output_tokens", lambda r: any(u.get("input") is not None or u.get("output") is not None for u in r.usage)),
    "agent_names": ("gen_ai.agent.name on agent or tool spans", lambda r: any(s.get("agent") for s in r.spans)),
    "user_input": ("user input messages (gen_ai.input.messages)", lambda r: bool((r.input or "").strip())),
    "final_answer": ("assistant output messages (gen_ai.output.messages)", lambda r: bool((r.answer or "").strip())),
    "state_changes": ("agentest.state_change events or agentest.final_state", lambda r: bool(r.effects) or bool(r.final_state)),
    "approvals": ("agentest.approval spans", lambda r: bool(r.approvals)),
}


def threshold(cli_value: float | None = None) -> float:
    """CLI value, else config ``thresholds.max_na_share``, else the default. Must lie in [0, 1]."""
    from agentest.standards import ext

    v = cli_value if cli_value is not None else (ext.CONFIG.get("thresholds") or {}).get("max_na_share", DEFAULT_MAX_NA)
    v = float(v)
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"max_na_share must be between 0 and 1, got {v}")
    return v


def signals(runs: list) -> dict[str, bool]:
    return {k: any(fn(r) for r in runs) for k, (_, fn) in SIGNALS.items()}


def agent_coverage(row: dict, max_na: float, sig: dict[str, bool] | None = None) -> dict:
    """Coverage of one agent's verdict row ``{id: {"status", "detail"}}``."""
    considered = {i: c for i, c in row.items() if not (c["status"] == "n/a" and "disabled by config" in c.get("detail", ""))}
    na = sum(c["status"] == "n/a" for c in considered.values())
    not_run = sum(c["status"] == "not-run" for c in considered.values())
    total = len(considered)
    share = (na + not_run) / total if total else 1.0
    out = {"considered": total, "n/a": na, "not-run": not_run,
           "not-assessed": sum(c["status"] == "not-assessed" for c in considered.values()),
           "na_share": round(share, 4), "max_na_share": max_na, "ok": share <= max_na}
    if sig is not None:
        out["signals_present"] = sorted(k for k, v in sig.items() if v)
        out["signals_missing"] = sorted(k for k, v in sig.items() if not v)
    return out


def gate(res: dict, max_na: float | None = None, runs: dict | None = None) -> dict:
    """Coverage for every agent in a verdict mapping. ``runs`` ({agent: [Run]}) adds the signal inventory."""
    t = threshold(max_na)
    agents = {a: agent_coverage(row, t, signals(runs[a]) if runs and a in runs else None) for a, row in res.items()}
    failing = sorted(a for a, c in agents.items() if not c["ok"])
    return {"rule": RULE_ID, "max_na_share": t, "ok": not failing, "failing": failing, "agents": agents}


def message(a: str, c: dict) -> str:
    miss = c.get("signals_missing")
    return (f"{a}: {c['na_share']:.0%} of {c['considered']} checks had no standard signal (n/a {c['n/a']}, not-run {c['not-run']}),"
            f" above the {c['max_na_share']:.0%} instrumentation-coverage threshold"
            + (f"; missing trace signals: {', '.join(miss)}" if miss else ""))
