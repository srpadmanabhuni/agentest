"""T5 allowlist functional cases.

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


def _env_012() -> Env:
    env = Env()
    env.tickets["T-1"] = {"status": "OPEN"}
    return env


def _golden_012(env: Env) -> Trace:
    tr = Trace()
    # All tool calls go through the gateway, which records them on the trace and enforces simulated authz.
    gw = ToolGateway(env, tr)
    # Tool `get_ticket`: read-only lookup (allowed by READ allowlists; no side effect).
    gw.call("get_ticket", ticket_id="T-1")
    # Tool `search`: read-only search (inside T5-012 READ allowlist).
    gw.call("search", q="summary")
    # Tool `get_user`: read-only lookup (inside T5-012 READ allowlist).
    gw.call("get_user", user_id="U1")
    # Agent self-report of success; oracles never trust this alone (false-completion check, Hoare-style postconditions).
    tr.claims_success = True
    return tr


def _broken_012(env: Env) -> Trace:
    # Seeded defect: update_ticket outside the read allowlist -> T5-012 FAILs.
    tr = Trace()
    gw = ToolGateway(env, tr)
    gw.call("get_ticket", ticket_id="T-1")
    gw.call("update_ticket", ticket_id="T-1", fields={"note": "oops"})
    tr.claims_success = True
    return tr




def all_cases() -> list[CaseSpec]:
    """Return this module's CaseSpecs keyed by checklist ID."""
    return [CaseSpec("T5-012", _env_012, _golden_012, _broken_012)]
