"""r12 core-47 harness signals (agent-agnostic, all optional; absent signal -> rules fall back to older evidence).

Root span (invoke_agent) attributes:
  agentest.task.spec          JSON {"goal": str, "postconditions": [{"path","op","value"}], "required_tools": [str],
                              "read_only": bool, "decision": bool}
  agentest.initial_state      JSON snapshot of the system of record before the run (agentest.final_state = after)
  agentest.postcondition.result  "pass" | "fail" (harness oracle evaluated task.spec on final_state)
  agentest.user.language      BCP-47 tag of the language the user writes in / set for the session
  agentest.run.status         "completed" | "failed" | "incomplete" as the agent reported it to the caller
Tool span attributes:
  agentest.tool.status        "ok" | "error" | "denied" (normalised by the harness)
State-change events (side-effect ledger): agentest.state_change.data may carry "object" (id) and "effect_id".
Budget / prerequisites stay in the governance extension (limits.max_tool_calls, prerequisites)."""
from __future__ import annotations

import json


def _j(v):
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v) if isinstance(v, str) and v.strip()[:1] in "{[" else None
    except ValueError:
        return None


def task_spec(r) -> dict | None:
    v = _j((r.attrs or {}).get("agentest.task.spec"))
    return v if isinstance(v, dict) else None


def initial_state(r) -> dict | None:
    v = _j((r.attrs or {}).get("agentest.initial_state"))
    return v if isinstance(v, dict) else None


def postcondition_result(r) -> bool | None:
    v = str((r.attrs or {}).get("agentest.postcondition.result", "")).strip().lower()
    return {"pass": True, "fail": False}.get(v)


def user_language(r) -> str | None:
    v = str((r.attrs or {}).get("agentest.user.language", "")).strip().lower()
    return v.split("-")[0] or None


def run_status(r) -> str | None:
    v = str((r.attrs or {}).get("agentest.run.status", "")).strip().lower()
    return v or None


def tool_status(t) -> str | None:
    v = str((t.attrs or {}).get("agentest.tool.status", "")).strip().lower()
    return v if v in ("ok", "error", "denied") else None


def ledger(r) -> list[tuple[str, str, str]]:
    """(effect, object, effect_id) per executed state change; object '' when the event names none."""
    out = []
    for e in r.executed():
        d = e.get("data") if isinstance(e.get("data"), dict) else {}
        out.append((str(e.get("effect", "")), str(d.get("object", "")), str(d.get("effect_id", ""))))
    return out


def state_diff(before: dict, after: dict, prefix: str = "") -> set[str]:
    """Dotted paths whose value differs between two snapshots."""
    out: set[str] = set()
    for k in set(before) | set(after):
        p = f"{prefix}{k}"
        a, b = before.get(k), after.get(k)
        if isinstance(a, dict) and isinstance(b, dict):
            out |= state_diff(a, b, p + ".")
        elif a != b:
            out.add(p)
    return out
