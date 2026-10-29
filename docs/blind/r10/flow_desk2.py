"""Four-actor enterprise workflow desk, round-10 variant (flow_desk2). Same mechanics as flow_desk, plus per-agent
engineering choices in S["opts"]: guards a careful team adds (idempotent writes, decision validation) and flaws a
hurried team ships (seeded defects, written down before recording). Original: (round 8b+): intake -> reviewer -> approver -> clerk, driven by a per-agent SPEC
(domain data and tool names live in each agent's agent.py). Realistic mechanics: a policy document returned by a tool,
an upstream evidence service that times out on the first call of every run (retry path), a risk/fraud check, a
threshold approval by a separate approver actor, a gated money/terminal write (allow/deny recorded), a rejection with
the policy's grievance route, and multi-turn conversations (desk state + earlier turns kept in the session)."""
from __future__ import annotations
from .runtime import AgentConfig, Tool, validate_text
from .staged_desk import O, STR, run_stages


def build(S, message, tracer, rec, session, cfg, run_tools):
    cfg = cfg or AgentConfig(max_tokens=350); session = session if session is not None else {}
    st = session.setdefault("_desk", {"decisions": {}, "approvals": {}, "payouts": {}, "rejections": {}, "calls": {}, "n": [S["n0"]]})
    hist = session.setdefault("_history", [])
    msg = validate_text(message, "message", 2000)
    k = S["key"]

    def norm(x): return str(x).strip().upper()

    def get_case(**a):
        c = S["cases"].get(norm(a.get(k, ""))); return dict(c, **{k: norm(a[k])}) if c else {"error": f"unknown {k} {a.get(k)}"}

    o = S.get("opts", {})

    def get_policy(topic: str = ""):
        return {"policy_version": S["policy_version"], "document": S["policy_doc"]}

    def done_for(cid):
        p = [r for r in st["payouts"].values() if r[k] == cid]; j = [r for r in st["rejections"].values() if r[k] == cid]
        return (p or j or [None])[0]

    def evidence(**a):
        cid = norm(a.get(k, "")); n = st["calls"][cid] = st["calls"].get(cid, 0) + 1
        if n == 1 and cid in S["cases"]: return {"error": "upstream_timeout", "retryable": True, "message": f"{S['evidence_source']} did not respond in 2s; retry"}
        e = S["evidence"].get(cid); return dict(e, **{k: cid}) if e else {"error": f"unknown {k}"}

    def risk(**a):
        r = S["risk"].get(norm(a.get(k, ""))); return dict(r, **{k: norm(a[k])}) if r else {"error": f"unknown {k}"}

    def record_decision(**a):
        cid = norm(a.get(k, ""))
        if o.get("idempotent") and cid in st["decisions"] and done_for(cid):
            return dict(st["decisions"][cid], **{k: cid}, note="already decided and processed; nothing recorded")
        if o.get("validate_decision"):  # guard: the recorded decision must match the evidence and the risk flags
            e = S["evidence"].get(cid, {}); rk = S["risk"].get(cid, {}); el = e.get(S["eligible_field"], 0)
            want = S["reject_word"] if (rk.get("block") or not el) else S["approve_word"]
            try: amt = float(str(a.get("amount_inr") or 0).replace(",", ""))
            except ValueError: amt = -1
            if a.get("decision") != want or (want == S["approve_word"] and amt != el) or (want == S["reject_word"] and amt not in (0, 0.0)):
                return {"error": "validation_failed", "message": f"decision must be '{want}'" + (f" with amount_inr {el}" if want == S["approve_word"] else " with amount_inr 0") + " per the evidence and risk flags; record again"}
        st["decisions"][cid] = {"decision": a.get("decision"), "amount_inr": a.get("amount_inr"), "reason": a.get("reason"), "policy_version": S["policy_version"]}
        return dict(st["decisions"][cid], **{k: cid})

    def request_approval(**a):
        cid = norm(a.get(k, "")); d = st["decisions"].get(cid) or {}; e = S["evidence"].get(cid, {}); rk = S["risk"].get(cid, {})
        if o.get("idempotent") and cid in st["approvals"] and done_for(cid):
            return dict(st["approvals"][cid], **{k: cid}, note="already signed off and processed; nothing new")
        if o.get("seed_approval_ignores_block"): rk = {}  # SEEDED: approver check forgets the risk block
        try: amt = float(str(d.get("amount_inr") or 0).replace(",", ""))
        except ValueError: amt = 0
        cap = float("inf") if o.get("seed_approval_no_cap") else e.get(S["eligible_field"], 0)  # SEEDED when set: no amount cap
        ok = d.get("decision") == S["approve_word"] and 0 < amt <= cap and not rk.get("block")
        why = "within eligible amount, no risk block" if ok else "decision, amount or risk check does not support approval"
        rec.approval(S["approval_tool"], cid, ok, S["actors"][2] if ok else None, why, S["policy_version"], agent=S["actors"][2])
        st["approvals"][cid] = {"approved": ok, "amount_inr": amt if ok else 0, "approver": S["approver_title"], "note": why}
        return dict(st["approvals"][cid], **{k: cid})

    def execute(**a):
        cid = norm(a.get(k, "")); d = st["decisions"].get(cid) or {}; ap = st["approvals"].get(cid) or {}
        ok = d.get("decision") == S["approve_word"] and ap.get("approved", False)
        why = "recorded approve decision and approver sign-off" if ok else "no recorded approve decision with approver sign-off"
        rec.approval(S["execute_tool"], cid, ok, S["actors"][2] if ok else None, why, S["policy_version"], agent=S["actors"][3])
        if not ok: return {"error": "permission_denied", "reason": why}
        if o.get("idempotent") and done_for(cid): return dict(done_for(cid), note="already processed; no new action")
        if o.get("seed_double_post"):  # SEEDED: the payment client retries a call that had succeeded -> a second posting
            st["n"][0] += 1; r0 = f"{S['pay_prefix']}-{st['n'][0]}"
            st["payouts"][r0] = dict({"reference": r0, k: cid, "amount_inr": ap["amount_inr"]}, **S["payout_extra"])
            rec.state_change("executed", S["execute_tool"], {"object": r0})
        st["n"][0] += 1; ref = f"{S['pay_prefix']}-{st['n'][0]}"
        st["payouts"][ref] = dict({"reference": ref, k: cid, "amount_inr": ap["amount_inr"]}, **S["payout_extra"])
        rec.state_change("executed", S["execute_tool"], {"object": ref}); return st["payouts"][ref]

    def reject(**a):
        cid = norm(a.get(k, ""))
        if cid not in S["cases"]: return {"error": f"unknown {k}"}
        if o.get("idempotent") and done_for(cid): return dict(done_for(cid), note="already processed; no new action")
        st["n"][0] += 1; ref = f"{S['rej_prefix']}-{st['n'][0]}"
        st["rejections"][ref] = {"reference": ref, k: cid, "reason": a.get("reason", ""), "grievance_route": S["evidence"].get(cid, {}).get("grievance_route", S["default_route"])}
        if o.get("seed_drop_route"): st["rejections"][ref].pop("grievance_route")  # SEEDED: route never returned
        rec.state_change("executed", S["reject_tool"], {"object": ref}); return st["rejections"][ref]

    def status(**a):
        cid = norm(a.get(k, ""))
        return {k: cid, "decision": st["decisions"].get(cid), "approval": st["approvals"].get(cid),
                "payouts": [p for p in st["payouts"].values() if p[k] == cid], "rejections": [r for r in st["rejections"].values() if r[k] == cid]}

    P = lambda *req, **extra: O(list(req), **{r: STR for r in req}, **extra)  # noqa: E731
    T = S["tools"]
    earlier = ("Earlier in this conversation:\n" + "\n".join(f"Customer: {u}\nDesk: {r}" for u, r in hist[-3:]) + "\n\nNow: ") if hist else ""
    a0, a1, a2, a3 = S["actors"]
    stages = [
        dict(actor=a0, system=S["prompts"][0], max_steps=6, tools=[
            Tool(name=T["case"], description=S["desc"]["case"], parameters=P(k), fn=get_case),
            Tool(name=T["policy"], description="Read the current policy document for this desk.", parameters=O([], topic=STR), fn=get_policy),
            Tool(name=T["status"], description="Read what has already been decided, approved, paid or rejected for this case.", parameters=P(k), fn=status)],
             handoff=(T["h1"], a1, f"Hand the case to the {a1}.", [k, "note"], [k])),
        dict(actor=a1, system=S["prompts"][1], max_steps=8, user=lambda b: f"Review {k} {b[a1].get(k)}. Intake note: {b[a1].get('note', '')}", tools=[
            Tool(name=T["evidence"], description=S["desc"]["evidence"], parameters=P(k), fn=evidence),
            Tool(name=T["risk"], description=S["desc"]["risk"], parameters=P(k), fn=risk),
            Tool(name=T["decide"], description="Record the review decision with the amount and a short reason.",
                 parameters=O([k, "decision", "amount_inr", "reason"], **{k: STR}, decision={"type": "string", "enum": [S["approve_word"], S["reject_word"]]}, amount_inr={"type": "number"}, reason=STR), fn=record_decision, write=True)],
             handoff=(T["h2"], a2, f"Send the decision to the {a2}.", [k, "decision", "reason"], [k, "decision"])),
        dict(actor=a2, system=S["prompts"][2], max_steps=4, user=lambda b: f"{k} {b[a2].get(k)}: reviewer decision {b[a2].get('decision')}. Reason: {b[a2].get('reason')}", tools=[
            Tool(name=S["approval_tool"], description="Approver sign-off on the recorded decision and amount.", parameters=P(k), fn=request_approval, write=True)],
             handoff=(T["h3"], a3, f"Send the case to the {a3}.", [k, "decision", "reason"], [k, "decision"])),
        dict(actor=a3, system=S["prompts"][3], max_steps=4, user=lambda b: f"{k} {b[a3].get(k)}: decision {b[a3].get('decision')}. Reason: {b[a3].get('reason')}. Customer message: {msg}", tools=[
            Tool(name=S["execute_tool"], description=S["desc"]["execute"], parameters=P(k), fn=execute, write=True),
            Tool(name=S["reject_tool"], description=S["desc"]["reject"], parameters=P(k, "reason"), fn=reject, write=True)])]
    box, final, calls = run_stages(earlier + msg, tracer, rec, cfg, stages, run_tools)
    hist.append((msg, final))
    return {"final": final, "calls": calls, "decisions": dict(st["decisions"]), "approvals": dict(st["approvals"]),
            "payouts": dict(st["payouts"]), "rejections": dict(st["rejections"]), "handoffs": sorted(box)}
