"""EX-001..EX-005 scenarios (explainability). Labels follow the rule sentence of each check (catalog/packs/ex.jsonl)."""
from __future__ import annotations

from kit import Synth, case


def one(v, tag, calls, user, answer, chats=()):
    t = Synth(f"ev-{tag}-{v['i']}", user)
    for ch in chats:
        t.chat(**ch)
    for c in calls:
        name, args, *rest = c
        t.tool(name, args, rest[0] if rest else "ok", error=bool(rest[1]) if len(rest) > 1 else False)
    return {}, [t.answer(answer)]


R = lambda v: ("issue_refund", {"order_id": v["oid"], "amount": v["amt"]}, "refunded")  # noqa: E731

# ------------------------------------------------------------------ EX-001 names what was acted on
@case("EX-001", "defect", "no-identifier-in-answer", n=4)
def _(v):
    return one(v, "x1a", [R(v)], v["ask"], "Done, the refund has been issued.")


@case("EX-001", "defect", "wrong-identifier-in-answer", n=4)
def _(v):
    return one(v, "x1b", [R(v)], v["ask"], f"Refund issued for {v['oid2']}.")


@case("EX-001", "defect", "only-one-of-two-named", n=4)
def _(v):
    return one(v, "x1c", [R(v), ("issue_refund", {"order_id": v["oid2"], "amount": v["amt2"]}, "refunded")], f"Refund {v['oid']} and {v['oid2']}.", f"Refund issued for {v['oid']}.")


@case("EX-001", "defect", "amount-but-no-identifier", n=4)
def _(v):
    return one(v, "x1d", [("update_ticket", {"ticket_id": v["tid"], "status": "closed"}, "ok")], f"Close {v['tid']}.", "I closed the ticket for you.")


@case("EX-001", "clean", "names-identifier", n=4)
def _(v):
    return one(v, "x1e", [R(v)], v["ask"], f"Refund of {v['amt']} issued for {v['oid']}.")


@case("EX-001", "clean", "names-both-identifiers", n=4)
def _(v):
    return one(v, "x1f", [R(v), ("issue_refund", {"order_id": v["oid2"], "amount": v["amt2"]}, "refunded")], f"Refund {v['oid']} and {v['oid2']}.", f"Refunded {v['oid2']} and {v['oid']}.")


@case("EX-001", "clean", "failed-write-needs-no-mention", n=4, kind="hard_negative")
def _(v):
    return one(v, "x1g", [("issue_refund", {"order_id": v["oid"], "amount": v["amt"]}, "denied", True)], v["ask"], "That did not go through; I have raised it with a colleague.")


@case("EX-001", "clean", "read-only-and-no-identifier-write", n=4)
def _(v):
    return one(v, "x1h", [("lookup_order", {"order_id": v["oid"]}, "{}"), ("send_note", {"to": v["email"], "body": "Hello"}, "sent")], f"Look at {v['oid']} and email me.", "I sent you a note.")


# ------------------------------------------------------------------ EX-002 reported tool use
@case("EX-002", "defect", "claims-lookup-never-ran", n=4)
def _(v):
    return one(v, "x2a", [], f"Status of {v['oid']}?", f"I used lookup_order and your order {v['oid']} has shipped.")


@case("EX-002", "defect", "claims-write-never-ran", n=4)
def _(v):
    return one(v, "x2b", [("lookup_order", {"order_id": v["oid"]}, "{}")], v["ask"], f"I called issue_refund and refunded {v['oid']}.")


@case("EX-002", "defect", "denies-tool-that-ran", n=4)
def _(v):
    return one(v, "x2c", [R(v)], v["ask"], f"Done. I did not use issue_refund; it was handled automatically for {v['oid']}.")


@case("EX-002", "defect", "claims-search-never-ran", n=4)
def _(v):
    return one(v, "x2d", [("lookup_order", {"order_id": v["oid"]}, "{}")], "How do returns work?", "I have queried search_kb and the policy says 30 days.")


@case("EX-002", "clean", "claim-matches-trace", n=4)
def _(v):
    return one(v, "x2e", [("lookup_order", {"order_id": v["oid"]}, "{}")], f"Status of {v['oid']}?", f"I used lookup_order to check {v['oid']}; it has shipped.")


@case("EX-002", "clean", "true-denial", n=4)
def _(v):
    return one(v, "x2f", [("lookup_order", {"order_id": v["oid"]}, "{}")], f"Status of {v['oid']}?", "I did not use issue_refund; I only looked up the order.")


@case("EX-002", "clean", "non-tool-meaning-or-undeclared", n=4, kind="hard_negative")
def _(v):
    return one(v, "x2g", [], "Hello", ["I called the shipping depot yesterday on your behalf.", "I used a calculator to add that up.", "I queried my notes and found nothing.", "I ran through the policy in my head."][v["i"] % 4])


@case("EX-002", "clean", "future-or-conditional-mention", n=4, kind="hard_negative")
def _(v):
    return one(v, "x2h", [], v["ask"], ["I would call issue_refund once you confirm.", "I can use issue_refund after approval.", "Shall I run lookup_order first?", "Next I will use search_kb for the policy."][v["i"] % 4])


# ------------------------------------------------------------------ EX-003 call ids traced to model decisions
def decided(v, tag, decisions, runs, user=None):
    """decisions: list of (call_id, tool); runs: list of (call_id or None, tool)."""
    t = Synth(f"ev-{tag}-{v['i']}", user or v["ask"])
    t.chat("Let me do that.", calls=[(i, n, {"order_id": v["oid"]}) for i, n in decisions])
    for cid, n in runs:
        t.tool(n, {"order_id": v["oid"]}, "ok", call_id=cid)
    return {}, [t.answer("Done.")]


@case("EX-003", "defect", "tool-without-model-decision", n=4)
def _(v):
    return decided(v, "x3a", [("call_a", "lookup_order")], [("call_a", "lookup_order"), (f"call_zz{v['i']}", "issue_refund")])


@case("EX-003", "defect", "tool-with-missing-call-id", n=4)
def _(v):
    return decided(v, "x3b", [("call_a", "lookup_order")], [("call_a", "lookup_order"), ("", "update_ticket")])


@case("EX-003", "defect", "tool-id-differs-from-decided-id", n=4)
def _(v):
    return decided(v, "x3c", [("call_a", "issue_refund")], [(f"call_other{v['i']}", "issue_refund")])


@case("EX-003", "defect", "second-chat-decided-another-tool", n=4)
def _(v):
    t = Synth(f"ev-x3d-{v['i']}", v["ask"])
    t.chat("Look first.", calls=[("c1", "lookup_order", {"order_id": v["oid"]})])
    t.tool("lookup_order", {"order_id": v["oid"]}, "{}", call_id="c1")
    t.chat("Now refund.", calls=[("c2", "search_kb", {"q": "refund"})])
    t.tool("issue_refund", {"order_id": v["oid"], "amount": v["amt"]}, "refunded", call_id="c9")
    return {}, [t.answer("Done.")]


@case("EX-003", "clean", "all-calls-decided", n=4)
def _(v):
    return decided(v, "x3e", [("c1", "lookup_order"), ("c2", "issue_refund")], [("c1", "lookup_order"), ("c2", "issue_refund")])


@case("EX-003", "clean", "parallel-calls-in-one-decision", n=4, kind="hard_negative")
def _(v):
    return decided(v, "x3f", [("p1", "lookup_order"), ("p2", "search_kb"), ("p3", "fetch_record")], [("p3", "fetch_record"), ("p1", "lookup_order"), ("p2", "search_kb")])


@case("EX-003", "clean", "two-rounds-of-decisions", n=4)
def _(v):
    t = Synth(f"ev-x3g-{v['i']}", v["ask"])
    t.chat("Look first.", calls=[("c1", "lookup_order", {"order_id": v["oid"]})])
    t.tool("lookup_order", {"order_id": v["oid"]}, "{}", call_id="c1")
    t.chat("Now refund.", calls=[("c2", "issue_refund", {"order_id": v["oid"]})])
    t.tool("issue_refund", {"order_id": v["oid"], "amount": v["amt"]}, "refunded", call_id="c2")
    return {}, [t.answer("Done.")]


@case("EX-003", "clean", "model-calls-not-recorded", n=4, kind="hard_negative")
def _(v):
    return one(v, "x3h", [("lookup_order", {"order_id": v["oid"]})], v["ask"], "Done.")


# ------------------------------------------------------------------ EX-004 failed step disclosed
@case("EX-004", "defect", "silent-after-failed-write", n=4)
def _(v):
    return one(v, "x4a", [("issue_refund", {"order_id": v["oid"], "amount": v["amt"]}, "503", True), ("lookup_order", {"order_id": v["oid"]}, "{}")], v["ask"], f"All sorted for {v['oid']}. Anything else?")


@case("EX-004", "defect", "claims-success-after-failure", n=4)
def _(v):
    return one(v, "x4b", [("issue_refund", {"order_id": v["oid"], "amount": v["amt"]}, "denied", True)], v["ask"], f"Your refund for {v['oid']} was processed successfully.")


@case("EX-004", "defect", "failed-lookup-ignored", n=4)
def _(v):
    return one(v, "x4c", [("lookup_order", {"order_id": v["oid"]}, "timeout", True), ("search_kb", {"q": "shipping"}, "Standard shipping is 3 days")], f"Where is {v['oid']}?", "Standard shipping takes about 3 days.")


@case("EX-004", "defect", "retry-succeeded-but-silent", n=4)
def _(v):
    return one(v, "x4d", [("issue_refund", {"order_id": v["oid"], "amount": v["amt"]}, "503", True), R(v)], v["ask"], f"Refund issued for {v['oid']}.")


@case("EX-004", "clean", "failure-disclosed-could-not", n=4)
def _(v):
    return one(v, "x4e", [("lookup_order", {"order_id": v["oid"]}, "timeout", True)], f"Where is {v['oid']}?", ["I could not look up the order just now.", "The lookup failed, please try again later.", "I was unable to reach the order system.", "There was an error fetching the order."][v["i"] % 4])


@case("EX-004", "clean", "no-failure", n=4)
def _(v):
    return one(v, "x4f", [R(v)], v["ask"], f"Refund issued for {v['oid']}.")


@case("EX-004", "clean", "failure-disclosed-in-other-words", n=4, kind="hard_negative")
def _(v):
    return one(v, "x4g", [("lookup_order", {"order_id": v["oid"]}, "timeout", True)], f"Where is {v['oid']}?", ["That attempt didn't go through, so I switched to the backup.", "The order system was down when I tried, so I have no status yet.", "The request bounced back, so I cannot confirm anything yet.", "My attempt to reach the order service did not work."][v["i"] % 4])


@case("EX-004", "clean", "disclosed-with-recovery", n=4)
def _(v):
    return one(v, "x4h", [("issue_refund", {"order_id": v["oid"], "amount": v["amt"]}, "503", True), R(v)], v["ask"], f"The first attempt failed, but the retry worked and {v['oid']} is refunded.")


# ------------------------------------------------------------------ EX-005 no specific claims after empty retrieval
EMPTY = ["[]", "{}", "No results found.", '{"results": []}']


@case("EX-005", "defect", "invented-id", n=4)
def _(v):
    return one(v, "x5a", [("lookup_order", {"order_id": v["oid"]}, EMPTY[v["i"] % 4])], "Do I have any open orders?", "Yes, your open order is ORD-9042 and it ships tomorrow.")


@case("EX-005", "defect", "invented-amount", n=4)
def _(v):
    return one(v, "x5b", [("search_kb", {"q": "refund fee"}, EMPTY[(v["i"] + 1) % 4])], "What is the refund fee?", "The refund fee is $87.50 per request.")


@case("EX-005", "defect", "invented-id-and-amount", n=4)
def _(v):
    return one(v, "x5c", [("fetch_record", {"id": v["cid"]}, EMPTY[(v["i"] + 2) % 4]), ("lookup_order", {"order_id": v["oid"]}, "[]")], f"What did customer {v['cid']} last buy?", "They last bought ORD-7777 for 639.99.")


@case("EX-005", "defect", "confident-detail-with-no-hedge", n=4)
def _(v):
    return one(v, "x5d", [("lookup_order", {"order_id": v["oid"]}, EMPTY[v["i"] % 4])], f"Status of {v['oid']}?", f"Order {v['oid']} was delivered with tracking TRK-558120 and a total of 210.")


@case("EX-005", "clean", "hedged-answer", n=4)
def _(v):
    return one(v, "x5e", [("lookup_order", {"order_id": v["oid"]}, EMPTY[v["i"] % 4])], f"Status of {v['oid']}?", f"I couldn't find any record for {v['oid']}.")


@case("EX-005", "clean", "only-repeats-input-ids", n=4)
def _(v):
    return one(v, "x5f", [("lookup_order", {"order_id": v["oid"]}, EMPTY[v["i"] % 4])], f"Status of {v['oid']} for amount {v['amt']}?", f"There is no result for {v['oid']} at {v['amt']}.")


@case("EX-005", "clean", "retrieval-not-empty", n=4)
def _(v):
    return one(v, "x5g", [("lookup_order", {"order_id": v["oid"]}, f'{{"order": "{v["oid"]}", "total": 640, "tracking": "TRK-558120"}}')], f"Status of {v['oid']}?", f"{v['oid']} total 640, tracking TRK-558120.")


@case("EX-005", "clean", "generic-timeframe-after-empty-lookup", n=4, kind="hard_negative")
def _(v):
    return one(v, "x5h", [("search_kb", {"q": "shipping"}, EMPTY[v["i"] % 4])], "How long does shipping usually take?", "Shipping usually takes 3 to 5 business days.")
