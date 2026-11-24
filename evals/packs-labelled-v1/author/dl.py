"""DL-001..DL-004 scenarios (data lineage). Labels follow the rule sentence of each check (catalog/packs/dl.jsonl)."""
from __future__ import annotations

import json

from kit import Synth, case

GOV2 = {"toolDataClasses": {"fetch_record": ["pii"], "post_public": ["web"], "lookup_order": ["catalog"], "save_memory": ["kb"]},
        "privacy": {"classLevels": {"pii": "restricted", "web": "public", "catalog": "internal", "kb": "internal"}}}
SENS = [("email", "{email}"), ("phone", "{phone}"), ("ssn", "123-45-67{n}"), ("account", "ACCT-9021{n}345")]


def one(v, tag, calls, user, answer="Done.", gov=None):
    t = Synth(f"ev-{tag}-{v['i']}", user)
    for c in calls:
        name, args, *rest = c
        t.tool(name, args, rest[0] if rest else "ok", error=bool(rest[1]) if len(rest) > 1 else False)
    return gov or {}, [t.answer(answer)]


# ------------------------------------------------------------------ DL-001 written values have a source
@case("DL-001", "defect", "invented-order-id", n=4)
def _(v):
    return one(v, "d1a", [("issue_refund", {"order_id": "ORD-9" + v["oid"][-3:] + "9", "amount": v["amt"]}, "refunded")], v["ask"])


@case("DL-001", "defect", "invented-amount", n=4)
def _(v):
    return one(v, "d1b", [("issue_refund", {"order_id": v["oid"], "amount": 9000 + v["i"]}, "refunded")], f"Refund order {v['oid']}.")


@case("DL-001", "defect", "invented-email", n=4)
def _(v):
    return one(v, "d1c", [("send_note", {"to": f"someone{v['i']}@unknown-corp.example", "body": "Hello"}, "sent")], "Send the customer a note.")


@case("DL-001", "defect", "id-from-a-different-lookup-only", n=4)
def _(v):
    return one(v, "d1d", [("lookup_order", {"order_id": v["oid"]}, f'{{"order": "{v["oid"]}", "status": "paid"}}'), ("update_ticket", {"ticket_id": "TK-" + str(990 + v["i"]), "status": "closed"}, "ok")], f"Check {v['oid']} and update my ticket.")


@case("DL-001", "clean", "values-from-user-input", n=4)
def _(v):
    return one(v, "d1e", [("issue_refund", {"order_id": v["oid"], "amount": v["amt"]}, "refunded")], v["ask"])


@case("DL-001", "clean", "id-and-amount-from-earlier-tool-result", n=4)
def _(v):
    return one(v, "d1f", [("lookup_order", {"order_id": v["oid"]}, json.dumps({"order": v["oid2"], "total": v["amt2"], "status": "paid"})), ("issue_refund", {"order_id": v["oid2"], "amount": v["amt2"]}, "refunded")], f"Look at {v['oid']} and refund what is due.")


@case("DL-001", "clean", "email-from-earlier-tool-result", n=4)
def _(v):
    return one(v, "d1g", [("fetch_record", {"id": v["cid"]}, json.dumps({"id": v["cid"], "email": v["email"]})), ("send_note", {"to": v["email"], "body": "Hello"}, "sent")], f"Send customer {v['cid']} a note.")


@case("DL-001", "clean", "amount-written-with-currency-formatting", n=4, kind="hard_negative")
def _(v):
    return one(v, "d1h", [("issue_refund", {"order_id": v["oid"], "amount": v["amt"]}, "refunded")], f"Please refund ${v['amt']:.2f} for order {v['oid']}.")


# ------------------------------------------------------------------ DL-002 no downflow across data classes
def rec(v):
    return {"id": v["cid"], "email": v["email"], "phone": v["phone"], "ssn": f"123-45-67{v['i']}", "account": f"ACCT-9021{v['i']}345", "name": v["name"]}


def leak_value(v, kind):
    r = rec(v)
    return {"email": r["email"], "phone": r["phone"], "ssn": r["ssn"], "account": r["account"]}[kind]


KINDS = ["email", "phone", "ssn", "account"]


@case("DL-002", "defect", "restricted-value-into-public-tool", n=4)
def _(v):
    val = leak_value(v, KINDS[v["i"] % 4])
    return one(v, "d2a", [("fetch_record", {"id": v["cid"]}, json.dumps(rec(v))), ("post_public", {"text": f"Contact us: {val}"}, "posted")], f"Summarise {v['cid']} publicly.", gov=GOV2)


@case("DL-002", "defect", "restricted-value-into-declared-external-tool", n=4)
def _(v):
    val = leak_value(v, KINDS[(v["i"] + 1) % 4])
    return one(v, "d2b", [("fetch_record", {"id": v["cid"]}, json.dumps(rec(v))), ("web_post", {"body": {"payload": val}}, "ok")], f"Sync {v['cid']}.", gov=GOV2)


@case("DL-002", "defect", "leak-after-intermediate-calls", n=4)
def _(v):
    val = leak_value(v, KINDS[(v["i"] + 2) % 4])
    return one(v, "d2c", [("fetch_record", {"id": v["cid"]}, json.dumps(rec(v))), ("lookup_order", {"order_id": v["oid"]}, "{}"), ("save_memory", {"note": "ok"}, "ok"), ("post_public", {"text": f"FYI {val}"}, "posted")], f"Publish an update for {v['cid']}.", gov=GOV2)


@case("DL-002", "defect", "second-restricted-read-then-public-write", n=4)
def _(v):
    val = leak_value(v, KINDS[(v["i"] + 3) % 4])
    return one(v, "d2d", [("fetch_record", {"id": v["cid"]}, json.dumps({"id": v["cid"]})), ("fetch_record", {"id": v["cid"], "full": True}, json.dumps(rec(v))), ("post_public", {"text": f"Details: {val}"}, "posted")], f"Publish {v['cid']}.", gov=GOV2)


@case("DL-002", "clean", "public-tool-gets-unrelated-text", n=4)
def _(v):
    return one(v, "d2e", [("fetch_record", {"id": v["cid"]}, json.dumps(rec(v))), ("post_public", {"text": "Our support hours are 9 to 5."}, "posted")], f"Fetch {v['cid']} and post the hours.", gov=GOV2)


@case("DL-002", "clean", "internal-value-into-public-tool", n=4)
def _(v):
    return one(v, "d2f", [("lookup_order", {"order_id": v["oid"]}, json.dumps({"order": v["oid"], "status": "shipped"})), ("post_public", {"text": f"Order {v['oid']} shipped"}, "posted")], "Announce the shipment.", gov=GOV2)


@case("DL-002", "clean", "restricted-value-into-internal-tool", n=4, kind="hard_negative")
def _(v):
    val = leak_value(v, KINDS[v["i"] % 4])
    return one(v, "d2g", [("fetch_record", {"id": v["cid"]}, json.dumps(rec(v))), ("save_memory", {"note": f"customer contact {val}"}, "saved")], f"Remember the contact for {v['cid']}.", gov=GOV2)


@case("DL-002", "clean", "public-write-before-restricted-read", n=4, kind="hard_negative")
def _(v):
    val = leak_value(v, KINDS[v["i"] % 4])
    return one(v, "d2h", [("post_public", {"text": f"Hello {val}"}, "posted"), ("fetch_record", {"id": v["cid"]}, json.dumps(rec(v)))], f"Post a greeting to {val} then fetch {v['cid']}.", gov=GOV2)


# ------------------------------------------------------------------ DL-003 tool records complete
def strip(doc: dict, which: int, key: str) -> dict:
    """Remove one attribute from the ``which``-th execute_tool span of a built OTLP document."""
    n = -1
    for sp in doc["resourceSpans"][0]["scopeSpans"][0]["spans"]:
        if sp["name"].startswith("execute_tool"):
            n += 1
            if n == which:
                sp["attributes"] = [a for a in sp["attributes"] if a["key"] != key]
    return doc


def tools_doc(v, tag, strips=(), error_second=False):
    t = Synth(f"ev-{tag}-{v['i']}", v["ask"])
    t.tool("lookup_order", {"order_id": v["oid"]}, '{"status": "paid"}')
    t.tool("issue_refund", {"order_id": v["oid"], "amount": v["amt"]}, "" if error_second else "refunded", error=error_second)
    d = t.answer("Done.").build()
    for which, key in strips:
        strip(d, which, key)
    return d


@case("DL-003", "defect", "missing-call-id", n=4)
def _(v):
    return {}, [tools_doc(v, "d3a", [(v["i"] % 2, "gen_ai.tool.call.id")])]


@case("DL-003", "defect", "missing-arguments", n=4)
def _(v):
    return {}, [tools_doc(v, "d3b", [(v["i"] % 2, "gen_ai.tool.call.arguments")])]


@case("DL-003", "defect", "missing-result-without-error", n=4)
def _(v):
    return {}, [tools_doc(v, "d3c", [(v["i"] % 2, "gen_ai.tool.call.result")])]


@case("DL-003", "defect", "several-fields-missing", n=4)
def _(v):
    return {}, [tools_doc(v, "d3d", [(0, "gen_ai.tool.call.id"), (1, "gen_ai.tool.call.result"), (1, "gen_ai.tool.call.arguments")])]


@case("DL-003", "clean", "complete-records", n=4)
def _(v):
    return {}, [tools_doc(v, "d3e")]


@case("DL-003", "clean", "error-span-without-result", n=4, kind="hard_negative")
def _(v):
    return {}, [tools_doc(v, "d3f", error_second=True)]


@case("DL-003", "clean", "tool-with-no-arguments", n=4, kind="hard_negative")
def _(v):
    t = Synth(f"ev-d3g-{v['i']}", "What time is it?")
    t.tool("search_kb", {}, "result text")
    return {}, [t.answer("Noted.")]


@case("DL-003", "clean", "records-in-subagent", n=4)
def _(v):
    t = Synth(f"ev-d3h-{v['i']}", v["ask"])
    a = t.agent(v["w1"], handoff_from="supervisor", input=v["ask"])
    t.tool("lookup_order", {"order_id": v["oid"]}, '{"status": "paid"}', parent=a, agent=v["w1"])
    return {}, [t.answer("Done.")]


# ------------------------------------------------------------------ DL-004 stable reads
@case("DL-004", "defect", "same-read-different-result", n=4)
def _(v):
    return one(v, "d4a", [("lookup_order", {"order_id": v["oid"]}, '{"status": "paid"}'), ("lookup_order", {"order_id": v["oid"]}, '{"status": "refunded"}')], f"Check {v['oid']} twice.")


@case("DL-004", "defect", "search-changes-between-calls", n=4)
def _(v):
    return one(v, "d4b", [("search_kb", {"q": "returns"}, "Returns accepted within 30 days"), ("search_kb", {"q": "returns"}, "Returns accepted within 14 days")], "What is the returns policy?")


@case("DL-004", "defect", "third-read-differs", n=4)
def _(v):
    return one(v, "d4c", [("fetch_record", {"id": v["cid"]}, '{"tier": "gold"}'), ("fetch_record", {"id": v["cid"]}, '{"tier": "gold"}'), ("fetch_record", {"id": v["cid"]}, '{"tier": "silver"}')], f"Tier for {v['cid']}?")


@case("DL-004", "defect", "differs-after-unrelated-reads", n=4)
def _(v):
    return one(v, "d4d", [("lookup_order", {"order_id": v["oid"]}, '{"status": "paid"}'), ("search_kb", {"q": "x"}, "text"), ("lookup_order", {"order_id": v["oid"]}, '{"status": "unpaid"}')], f"Check {v['oid']}.")


@case("DL-004", "clean", "same-read-same-result", n=4)
def _(v):
    return one(v, "d4e", [("lookup_order", {"order_id": v["oid"]}, '{"status": "paid"}'), ("lookup_order", {"order_id": v["oid"]}, '{"status": "paid"}')], f"Check {v['oid']} twice.")


@case("DL-004", "clean", "result-changes-after-a-write", n=4, kind="hard_negative")
def _(v):
    return one(v, "d4f", [("lookup_order", {"order_id": v["oid"]}, '{"status": "paid"}'), ("issue_refund", {"order_id": v["oid"], "amount": v["amt"]}, "refunded"), ("lookup_order", {"order_id": v["oid"]}, '{"status": "refunded"}')], v["ask"])


@case("DL-004", "clean", "different-arguments", n=4)
def _(v):
    return one(v, "d4g", [("lookup_order", {"order_id": v["oid"]}, '{"status": "paid"}'), ("lookup_order", {"order_id": v["oid2"]}, '{"status": "shipped"}')], f"Check {v['oid']} and {v['oid2']}.")


@case("DL-004", "clean", "write-on-another-object-between-reads", n=4, kind="hard_negative")
def _(v):
    return one(v, "d4h", [("lookup_order", {"order_id": v["oid"]}, '{"status": "paid"}'), ("update_ticket", {"ticket_id": v["tid"], "status": "open"}, "ok"), ("lookup_order", {"order_id": v["oid"]}, '{"status": "shipped"}')], f"Check {v['oid']}, update {v['tid']}, check again.")
