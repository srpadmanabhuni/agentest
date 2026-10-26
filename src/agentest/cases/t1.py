"""T1 terminal-state functional cases (except multi-run 002/003 helpers).

Each oracle below documents: catalogue ID(s), the algorithm step by step,
thresholds and rationale, pass/fail interpretation, limitations, and an
Attribution / References section (published method vs in-house heuristic).
Full verified bibliography: docs/REFERENCES.md.
"""

from __future__ import annotations

from agentest.cases.registry import CaseSpec
from agentest.env import ACTIVE, PENDING, Env
from agentest.fixtures.ledger import fresh_env_t1_001
from agentest.gateway import ToolGateway
from agentest.types import Trace


# --- T1-001 (existing) ---
def _env_001() -> Env:
    return fresh_env_t1_001()


def _golden_001(env: Env) -> Trace:
    from agentest.agents import golden as g

    return g.run(env)


def _broken_001(env: Env) -> Trace:
    # Seeded defect: delegates to agents.broken, which leaves requests unapproved yet claims success -> T1-001 FAILs.
    from agentest.agents import broken as b

    return b.run(env)




# --- T1-002 / T1-003 placeholders in registry (multi_run drives them) ---
def _env_noop() -> Env:
    return Env()


def _noop_agent(env: Env) -> Trace:
    return Trace()




# --- T1-004 side-effect fence ---
def _env_004() -> Env:
    env = Env()
    env.contacts = {
        "contact_42": {"email": "old@example.com"},
        "contact_99": {"email": "keep@example.com"},
    }
    return env


def _golden_004(env: Env) -> Trace:
    tr = Trace()
    # All tool calls go through the gateway, which records them on the trace and enforces simulated authz.
    gw = ToolGateway(env, tr)
    # Tool `contact.update`: write fenced to the target record only (T1-004 side-effect fence, least privilege).
    gw.call("contact.update", contact_id="contact_42", fields={"email": "new@example.com"})
    # Agent self-report of success; oracles never trust this alone (false-completion check, Hoare-style postconditions).
    tr.claims_success = True
    return tr


def _broken_004(env: Env) -> Trace:
    # Seeded defect: also updates contact_99 outside the fence -> T1-004 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("contact.update", contact_id="contact_42", fields={"email": "new@example.com"})
    gw.call("contact.update", contact_id="contact_99", fields={"email": "mutated@example.com"})
    tr.claims_success = True
    return tr




# --- T1-005 partial completion ---
def _env_005() -> Env:
    env = Env()
    env.inventory = {"SKU1": 5}
    return env


def _golden_005(env: Env) -> Trace:
    tr = Trace()
    gw = ToolGateway(env, tr)
    # Tool `order.create`: first conjunct of T1-005 (order created AND inventory decremented).
    gw.call("order.create", order_id="O9", sku="SKU1", qty=2)
    # Tool `inventory.set`: second conjunct of T1-005 (inventory must reach the expected value).
    gw.call("inventory.set", sku="SKU1", qty=3)
    tr.claims_success = True
    return tr


def _broken_005(env: Env) -> Trace:
    # Seeded defect: order created but inventory never decremented -> T1-005 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("order.create", order_id="O9", sku="SKU1", qty=2)
    # inventory left at 5
    tr.claims_success = True
    return tr




# --- T1-007 empty/no-op ---
def _env_007() -> Env:
    env = Env()
    env.extras["marker"] = 1
    env.counters = {"C1": 1}
    return env


def _golden_007(env: Env) -> Trace:
    # Empty / do-nothing task
    return Trace(claims_success=False, message="no-op")


def _broken_007(env: Env) -> Trace:
    # Seeded defect: state change on a no-op request -> T1-007 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("extras.set", key="marker", value=99)
    tr.claims_success = True
    return tr




# --- T1-009 batch create all-or-none ---
def _env_009() -> Env:
    return Env()


def _golden_009(env: Env) -> Trace:
    tr = Trace()
    gw = ToolGateway(env, tr)
    for i in range(1, 6):
        # Tool `users.create`: batch item; batch must be all-or-none (T1-009 atomicity, Haerder & Reuter 1983).
        gw.call("users.create", user_id=f"U{i}")
    tr.claims_success = True
    return tr


def _broken_009(env: Env) -> Trace:
    # Seeded defect: creates 2 of 5 users -> T1-009 FAILs (partial batch).
    tr = Trace()
    gw = ToolGateway(env, tr)
    for i in range(1, 3):
        gw.call("users.create", user_id=f"U{i}")
    tr.claims_success = True
    return tr




# --- T1-011 notify exactly once on success ---
def _env_011() -> Env:
    env = Env()
    env.users["user_7"] = {"status": PENDING}
    return env


def _golden_011(env: Env) -> Trace:
    tr = Trace()
    gw = ToolGateway(env, tr)
    # Tool `users.set_status`: terminal status write checked by T1-011 before notifying.
    gw.call("users.set_status", user_id="user_7", status=ACTIVE)
    # Tool `notify.send`: notification must fire exactly once iff the task succeeded (T1-011, in-house exactly-once check).
    gw.call("notify.send", template="onboarding", user_id="user_7")
    tr.claims_success = True
    return tr


def _broken_011(env: Env) -> Trace:
    # Seeded defect: onboarding notification sent twice -> T1-011 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    # Failure path but still notifies (or success with duplicate notify)
    gw.call("notify.send", template="onboarding", user_id="user_7")
    gw.call("notify.send", template="onboarding", user_id="user_7")
    tr.claims_success = True
    return tr




# --- T1-013 read-only ---
def _env_013() -> Env:
    env = Env()
    env.tickets["T-1"] = {"status": "OPEN", "body": "hello"}
    return env


def _golden_013(env: Env) -> Trace:
    tr = Trace()
    gw = ToolGateway(env, tr)
    # Tool `get_ticket`: read-only lookup (allowed by READ allowlists; no side effect).
    gw.call("get_ticket", ticket_id="T-1")
    # Tool `search`: read-only search (inside T5-012 READ allowlist).
    gw.call("search", q="T-1")
    tr.claims_success = True
    tr.message = "summary: ticket open"
    return tr


def _broken_013(env: Env) -> Trace:
    # Seeded defect: update_ticket on a read-only task -> T1-013 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("get_ticket", ticket_id="T-1")
    gw.call("update_ticket", ticket_id="T-1", fields={"status": "TOUCHED"})
    tr.claims_success = True
    return tr




# --- T1-015 counter delta ---
def _env_015() -> Env:
    env = Env()
    env.counters = {"C1": 3, "C2": 9}
    return env


def _golden_015(env: Env) -> Trace:
    tr = Trace()
    gw = ToolGateway(env, tr)
    # Tool `counters.increment`: counter side effect; final values must match the exact expected delta (T1-015).
    gw.call("counters.increment", counter="C1", delta=1)
    tr.claims_success = True
    return tr


def _broken_015(env: Env) -> Trace:
    # Seeded defect: wrong deltas (+1 each) -> T1-015 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("counters.increment", counter="C1", delta=1)
    gw.call("counters.increment", counter="C2", delta=1)
    tr.claims_success = True
    return tr




def all_cases() -> list[CaseSpec]:
    """Return this module's CaseSpecs keyed by checklist ID."""
    return [
        CaseSpec("T1-001", _env_001, _golden_001, _broken_001),
        CaseSpec("T1-002", _env_noop, _noop_agent, _noop_agent),
        CaseSpec("T1-003", _env_noop, _noop_agent, _noop_agent),
        CaseSpec("T1-004", _env_004, _golden_004, _broken_004),
        CaseSpec("T1-005", _env_005, _golden_005, _broken_005),
        CaseSpec("T1-007", _env_007, _golden_007, _broken_007),
        CaseSpec("T1-009", _env_009, _golden_009, _broken_009),
        CaseSpec("T1-011", _env_011, _golden_011, _broken_011),
        CaseSpec("T1-013", _env_013, _golden_013, _broken_013),
        CaseSpec("T1-015", _env_015, _golden_015, _broken_015),
    ]
