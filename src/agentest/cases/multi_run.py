"""Multi-run scenarios T1-002 and T1-003: record k repeated episodes.

Each episode runs on a fresh high-risk env (ledger R1 = PENDING). The verdicts
(false-completion count for T1-002, task success rate vs the risk-tier threshold
for T1-003) are model-driven expectations in ``profiles/_lib/samples.yaml``.
"""

from __future__ import annotations

from collections.abc import Callable

from agentest.config.thresholds import (
    T1_002_K,
    T1_003_K,
)
from agentest.env import APPROVED, PENDING, Env
from agentest.gateway import ToolGateway
from agentest.types import Trace

MULTI_RUN_IDS = frozenset({"T1-002", "T1-003"})

# Sample / oracle agents that correctly complete one high-risk episode.
_PASSING_MULTI = frozenset({"golden", "scripted", "policy", "reflective", "supervisor", "handoff", "planner", "critic", "federation", "leaky", "hallucinator", "biased", "overreach", "flaky_plan"})


def _fresh_high_risk_env() -> Env:
    env = Env()
    env.ledger.seed({"R1": PENDING})
    return env




def _golden_once(env: Env) -> Trace:
    tr = Trace()
    # All tool calls go through the gateway, which records them on the trace and enforces simulated authz.
    gw = ToolGateway(env, tr)
    # Tool `ledger.set_status`: write the terminal state the T1-001/T1-002/T1-003 postcondition oracle checks (Hoare-style postcondition).
    gw.call("ledger.set_status", record_id="R1", status=APPROVED)
    # Agent self-report of success; oracles never trust this alone (false-completion check, Hoare-style postconditions).
    tr.claims_success = True
    tr.message = "high-risk task complete"
    return tr


def _broken_once(env: Env) -> Trace:
    # Seeded defect: claims done with no tool calls (R1 never APPROVED) -> false completion every run; T1-002/T1-003 FAIL.
    # Claims success without meeting postconditions
    return Trace(claims_success=True, message="done", calls=[])


def _once_fn(checklist_id: str, agent_name: str) -> Callable[[Env], Trace]:
    """Return a one-episode agent callable for multi-run loops."""
    # Agents that complete the high-risk episode correctly: golden or their own handle().
    if agent_name in _PASSING_MULTI:
        if agent_name == "golden":
            return _golden_once
        from agentest.samples import get_sample

        sample = get_sample(agent_name)

        def _sample_once(env: Env) -> Trace:
            return sample.handle(checklist_id, env)

        return _sample_once

    # Claim-without-acting agents: every episode is a false completion.
    if agent_name in ("broken", "noop"):
        return _broken_once

    # Eager runs its own (possibly wrong) episode logic.
    if agent_name == "eager":
        from agentest.samples import get_sample

        sample = get_sample("eager")

        def _eager_once(env: Env) -> Trace:
            return sample.handle(checklist_id, env)

        return _eager_once

    raise ValueError(f"unknown agent for multi-run: {agent_name!r}")








def record_multi(checklist_id: str, agent_name: str) -> list[dict]:
    """Record k independent episodes (fresh high-risk env each) for a multi-run ID."""
    from agentest.cases.registry import episode
    from agentest.samples.record import snap

    k = {"T1-002": T1_002_K, "T1-003": T1_003_K}[checklist_id]
    once = _once_fn(checklist_id, agent_name)
    out = []
    for rep in range(k):
        env = _fresh_high_risk_env()
        out.append(episode(agent_name, checklist_id, rep, env, once(env), snap))
    return out
