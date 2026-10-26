"""T6 multi-turn state functional cases.

Each oracle below documents: catalogue ID(s), the algorithm step by step,
thresholds and rationale, pass/fail interpretation, limitations, and an
Attribution / References section (published method vs in-house heuristic).
Full verified bibliography: docs/REFERENCES.md.
"""

from __future__ import annotations

from agentest.cases.registry import CaseSpec
from agentest.env import Env
from agentest.gateway import ToolGateway
from agentest.types import Trace


def _env() -> Env:
    return Env()


# --- T6-003 binding stability ---
def _golden_003(env: Env) -> Trace:
    tr = Trace()
    # All tool calls go through the gateway, which records them on the trace and enforces simulated authz.
    gw = ToolGateway(env, tr)
    # Tool `ticket.open`: binds ticket_id for the conversation; re-binding to another id is the T6-003 failure (in-house).
    gw.call("ticket.open", ticket_id="T-9", order="O1")
    # Tool `ticket.comment`: turn-2 action on the bound ticket (T6-003).
    gw.call("ticket.comment", text="urgent")
    # Tool `ticket.close`: closes the currently bound ticket (T6-003).
    gw.call("ticket.close")
    # Agent self-report of success; oracles never trust this alone (false-completion check, Hoare-style postconditions).
    tr.claims_success = True
    return tr


def _broken_003(env: Env) -> Trace:
    # Seeded defect: re-opens T-OTHER mid-task (binding switch) -> T6-003 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("ticket.open", ticket_id="T-9", order="O1")
    gw.call("ticket.comment", text="urgent")
    # Switch binding to wrong id
    gw.call("ticket.open", ticket_id="T-OTHER", order="O2")
    gw.call("ticket.close")
    tr.claims_success = True
    return tr




# --- T6-006 completed monotonic ---
def _golden_006(env: Env) -> Trace:
    tr = Trace()
    gw = ToolGateway(env, tr)
    # Tool `todo.plan`: record the plan BEFORE side effects (plan-then-act, cf. Plan-and-Solve, Wang et al. 2023).
    gw.call("todo.plan", steps=["step1", "step2", "step3"])
    # Simulate turns: completed grows
    snapshots: list[set[str]] = []
    # Tool `todo.complete`: mark a plan step done; the completed set must only grow (T6-006 monotonic, in-house).
    gw.call("todo.complete", step="step1")
    snapshots.append(set(env.state.completed))
    gw.call("todo.complete", step="step2")
    snapshots.append(set(env.state.completed))
    # Stash for oracle
    env.extras["completed_snapshots"] = [sorted(s) for s in snapshots]
    tr.claims_success = True
    return tr


def _broken_006(env: Env) -> Trace:
    # Seeded defect: todo.drop shrinks the completed set -> T6-006 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("todo.plan", steps=["step1", "step2", "step3"])
    gw.call("todo.complete", step="step1")
    gw.call("todo.complete", step="step2")
    snap1 = sorted(env.state.completed)
    gw.call("todo.drop", step="step1")  # shrinks completed
    snap2 = sorted(env.state.completed)
    env.extras["completed_snapshots"] = [snap1, snap2]
    tr.claims_success = True
    return tr




# --- T6-010 locale persistence ---
def _golden_010(env: Env) -> Trace:
    tr = Trace()
    gw = ToolGateway(env, tr)
    # Tool `locale.set`: user locale; must persist across turns (T6-010).
    gw.call("locale.set", locale="hi")
    # Later turn: answer order status without resetting locale
    gw.call("get_ticket", ticket_id="order-status")
    tr.claims_success = True
    tr.message = "आपका ऑर्डर मार्ग में है"
    return tr


def _broken_010(env: Env) -> Trace:
    # Seeded defect: locale switched hi -> en -> T6-010 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("locale.set", locale="hi")
    gw.call("locale.set", locale="en")  # drift
    gw.call("get_ticket", ticket_id="order-status")
    tr.claims_success = True
    tr.message = "Your order is on the way"
    return tr




def all_cases() -> list[CaseSpec]:
    """Return this module's CaseSpecs keyed by checklist ID."""
    return [
        CaseSpec("T6-003", _env, _golden_003, _broken_003),
        CaseSpec("T6-006", _env, _golden_006, _broken_006),
        CaseSpec("T6-010", _env, _golden_010, _broken_010),
    ]
