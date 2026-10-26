"""T2 tool-ordering functional cases.

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




# --- T2-001 ---
def _golden_001(env: Env) -> Trace:
    tr = Trace()
    # All tool calls go through the gateway, which records them on the trace and enforces simulated authz.
    gw = ToolGateway(env, tr)
    # Tool `sanctions_screen`: prerequisite of open_account (T2-001).
    gw.call("sanctions_screen", customer="C1")
    # Tool `verify_identity`: identity check that must precede any disclose_* / open_account (T2-005, T2-001 DEPENDS_ON; NIST SP 800-63B).
    gw.call("verify_identity", customer="C1")
    # Tool `open_account`: guarded by DEPENDS_ON {sanctions_screen, verify_identity} (T2-001).
    gw.call("open_account", customer="C1")
    # Agent self-report of success; oracles never trust this alone (false-completion check, Hoare-style postconditions).
    tr.claims_success = True
    return tr


def _broken_001(env: Env) -> Trace:
    # Seeded defect: open_account without its prerequisites -> T2-001 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("open_account", customer="C1")  # skipped prereqs
    tr.claims_success = True
    return tr




# --- T2-003 ---
def _golden_003(env: Env) -> Trace:
    tr = Trace()
    gw = ToolGateway(env, tr)
    # Tool `disburse`: irreversible, single-shot disbursement; needs prior approval.grant (T2-004, EU AI Act Art. 14 human oversight) and at most one call (T2-003).
    gw.call("disburse", loan="L1", amount=100)
    tr.claims_success = True
    return tr


def _broken_003(env: Env) -> Trace:
    # Seeded defect: single-shot disburse called twice -> T2-003 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("disburse", loan="L1", amount=100)
    gw.call("disburse", loan="L1", amount=100)  # duplicate
    tr.claims_success = True
    return tr




# --- T2-009 ---
def _golden_009(env: Env) -> Trace:
    tr = Trace()
    gw = ToolGateway(env, tr)
    # Tool `fetch_prefs`: sibling read; any order with fetch_profile is fine before write_summary (T2-009).
    gw.call("fetch_prefs", user="U1")
    # Tool `fetch_profile`: sibling read; any order with fetch_prefs is fine before write_summary (T2-009).
    gw.call("fetch_profile", user="U1")
    # Tool `write_summary`: write step that depends on prior reads (T2-009 DEPENDS_ON graph, topological order per Kahn 1962).
    gw.call("write_summary", text="profile+prefs")
    tr.claims_success = True
    return tr


def _broken_009(env: Env) -> Trace:
    # Seeded defect: write_summary before its fetch prerequisites -> T2-009 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("write_summary", text="early")
    gw.call("fetch_profile", user="U1")
    tr.claims_success = True
    return tr




# --- T2-013 ---
def _golden_013(env: Env) -> Trace:
    tr = Trace()
    gw = ToolGateway(env, tr)
    # Tool `log_debug`: soft / harmless step; order is not constrained (T2-013 soft edge) and never privileged.
    gw.call("log_debug", msg="start")
    # Tool `authorize`: prerequisite of charge (T2-013 hard edge).
    gw.call("authorize", cart="CART1")
    gw.call("log_debug", msg="mid")
    # Tool `charge`: hard edge: must come after authorize (T2-013).
    gw.call("charge", cart="CART1")
    tr.claims_success = True
    return tr


def _broken_013(env: Env) -> Trace:
    # Seeded defect: charge before authorize -> T2-013 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("log_debug", msg="start")
    gw.call("charge", cart="CART1")  # before authorize
    gw.call("authorize", cart="CART1")
    tr.claims_success = True
    return tr




def all_cases() -> list[CaseSpec]:
    """Return this module's CaseSpecs keyed by checklist ID."""
    return [
        CaseSpec("T2-001", _env, _golden_001, _broken_001),
        CaseSpec("T2-003", _env, _golden_003, _broken_003),
        CaseSpec("T2-009", _env, _golden_009, _broken_009),
        CaseSpec("T2-013", _env, _golden_013, _broken_013),
    ]
