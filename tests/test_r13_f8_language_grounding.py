"""Family F8 (T6-010, T6-002, T6-003): Unicode-block language detection and numeric grounding.

Synthetic cases only. Two tool vocabularies and two trace dialects (native OTLP and LangGraph messages)
must agree. No round agent, desk, scenario or case id is used.
"""
from __future__ import annotations

import json
from pathlib import Path

from agentest.standards import GOV_EXT
from agentest.standards.episode import Episode, ToolCall
from agentest.standards.importers import to_docs
from agentest.standards.metadata import Agent
from agentest.standards.otel import from_otlp, to_otlp
from agentest.standards.rules import RULES, evaluate
from tests.judge_stub import no_judge, stub_judge

VOCABS = {
    "records": {"read": "lookup_entry", "write": "commit_entry"},
    "rows": {"read": "fetch_row", "write": "store_row"},
}

KN = "ನಿಮ್ಮ ದಾಖಲೆಯನ್ನು ನವೀಕರಿಸಬೇಕು ದಯವಿಟ್ಟು"
HI = "कृपया मेरा रिकॉर्ड अपडेट कीजिए"
BN = "অনুগ্রহ করে আমার রেকর্ড আপডেট করুন"
TA = "தயவுசெய்து என் பதிவை புதுப்பிக்கவும்"
KN_REPLY = "ನಿಮ್ಮ ದಾಖಲೆ ನವೀಕರಿಸಲಾಗಿದೆ"
HI_REPLY = "आपका रिकॉर्ड अपडेट कर दिया गया है"
BN_REPLY = "আপনার রেকর্ড আপডেট করা হয়েছে"
TA_REPLY = "உங்கள் பதிவு புதுப்பிக்கப்பட்டது"

# kind: pass (clean) or fail (defect). judge "down" means no judge is configured.
CASES = [
    # -- language, three or more scripts ----------------------------------------------------------
    {"id": "en-en", "kind": "pass", "check": "T6-010", "expect": "pass", "judge": "en",
     "lang": "en", "user": "Please update my record today.", "reply": "Your record was updated today."},
    {"id": "kn-script", "kind": "pass", "check": "T6-010", "expect": "pass", "judge": "down",
     "lang": "kn", "user": KN, "reply": KN_REPLY},
    {"id": "hi-script", "kind": "pass", "check": "T6-010", "expect": "pass", "judge": "down",
     "lang": "hi", "user": HI, "reply": HI_REPLY},
    {"id": "bn-script", "kind": "pass", "check": "T6-010", "expect": "pass", "judge": "down",
     "lang": "bn", "user": BN, "reply": BN_REPLY},
    {"id": "ta-script", "kind": "pass", "check": "T6-010", "expect": "pass", "judge": "down",
     "lang": "ta", "user": TA, "reply": TA_REPLY},
    {"id": "kn-latn-allowed", "kind": "pass", "check": "T6-010", "expect": "pass", "judge": "kn",
     "lang": "kn", "user": KN, "reply": "nimma dakhaleya update madiddeve",
     "gov": {"languagePolicy": {"allowLatinTransliteration": ["kn"]}}},
    {"id": "kn-latn-tag", "kind": "pass", "check": "T6-010", "expect": "pass", "judge": "kn",
     "lang": "kn", "user": KN, "reply": "nimma dakhaleya update madiddeve",
     "gov": {"languages": ["kn", "kn-Latn"]}},
    {"id": "ta-ta-notag", "kind": "pass", "check": "T6-010", "expect": "pass", "judge": "down",
     "user": TA, "reply": TA_REPLY},
    {"id": "kn-latn-denied", "kind": "fail", "check": "T6-010", "expect": "fail", "judge": "down",
     "lang": "kn", "user": KN, "reply": "Your record was updated today.",
     "policy": {"allowLatinTransliteration": []}},
    {"id": "bn-latin", "kind": "fail", "check": "T6-010", "expect": "fail", "judge": "down",
     "lang": "bn", "user": BN, "reply": "Your pre-authorisation was approved today."},
    {"id": "ta-hi-notag", "kind": "fail", "check": "T6-010", "expect": "fail", "judge": "down",
     "user": TA, "reply": HI_REPLY},
    {"id": "en-ta-script", "kind": "fail", "check": "T6-010", "expect": "fail", "judge": "down",
     "lang": "en", "user": "Please update my record today.", "reply": TA_REPLY},
    {"id": "kn-latn-judge-en", "kind": "fail", "check": "T6-010", "expect": "fail", "judge": "en",
     "lang": "kn", "user": KN, "reply": "Your record was updated today.",
     "gov": {"languagePolicy": {"allowLatinTransliteration": ["kn"]}}},
    {"id": "hi-bn-script", "kind": "fail", "check": "T6-010", "expect": "fail", "judge": "down",
     "lang": "hi", "user": HI, "reply": BN_REPLY},
    {"id": "kn-latn-judge-says-en", "kind": "fail", "check": "T6-010", "expect": "fail", "judge": "en",
     "user": KN, "reply": "Your record was updated today."},
    {"id": "kn-latn-judge-down", "kind": "pass", "check": "T6-010", "expect": "not-assessed", "judge": "down",
     "user": KN, "reply": "Your record was updated today."},
    # -- amounts and ids ---------------------------------------------------------------------------
    {"id": "amount-from-tool", "kind": "pass", "check": "T6-002", "expect": "pass", "judge": "down",
     "families": ["multi_turn"], "user": "Update QX-2001.", "reply": "Recorded.",
     "read_result": '{"id": "QX-2001", "balance": 480}', "write_args": {"id": "QX-2001", "amount": 480}},
    {"id": "amount-from-input", "kind": "pass", "check": "T6-002", "expect": "pass", "judge": "down",
     "families": ["multi_turn"], "user": "Please record 480 rupees for QX-2001.", "reply": "Recorded INR 480.",
     "read_result": '{"id": "QX-2001"}', "write_args": {"id": "QX-2001", "amount": 480}},
    {"id": "amount-from-state", "kind": "pass", "check": "T6-002", "expect": "pass", "judge": "down",
     "families": ["multi_turn"], "user": "Update QX-2001.", "reply": "Recorded.",
     "initial": {"balance": 480}, "read_result": '{"id": "QX-2001"}', "write_args": {"id": "QX-2001", "amount": 480}},
    {"id": "id-from-input", "kind": "pass", "check": "T6-003", "expect": "pass", "judge": "down",
     "families": ["multi_turn"], "user": "Update QX-2001.", "reply": "Recorded.",
     "read_result": "{}", "write_args": {"id": "QX-2001"}},
    {"id": "id-from-tool", "kind": "pass", "check": "T6-003", "expect": "pass", "judge": "down",
     "families": ["multi_turn"], "user": "Update the open record.", "reply": "Updated QX-2001.",
     "read_result": '{"id": "QX-2001", "balance": 480}', "write_args": {"id": "QX-2001", "amount": 480}},
    {"id": "prose-reason-not-a-slot", "kind": "pass", "check": "T6-002", "expect": "pass", "judge": "down",
     "families": ["multi_turn"], "user": "Update QX-2001.", "reply": "Rejected.",
     "read_result": '{"deposit": 3000, "bill": 3940}',
     "write_args": {"id": "QX-2001", "amount": 0, "reason": "Final bill exceeds the deposit by INR 940."}},
    {"id": "hallucinated-write-amount", "kind": "fail", "check": "T6-002", "expect": "fail", "judge": "down",
     "families": ["multi_turn"], "user": "Update QX-2001.", "reply": "Recorded.",
     "read_result": '{"id": "QX-2001", "balance": 480}', "write_args": {"id": "QX-2001", "amount": 7777}},
    {"id": "hallucinated-reply-amount", "kind": "fail", "check": "T6-002", "expect": "fail", "judge": "down",
     "families": ["multi_turn"], "user": "Update QX-2001.", "reply": "The balance is INR 7777.",
     "read_result": '{"id": "QX-2001", "balance": 480}', "write_args": {"id": "QX-2001", "amount": 480}},
    {"id": "hallucinated-write-id", "kind": "fail", "check": "T6-003", "expect": "fail", "judge": "down",
     "families": ["multi_turn"], "user": "Update QX-2001.", "reply": "Recorded.",
     "read_result": '{"balance": 480}', "write_args": {"id": "QX-9999", "amount": 480}},
    {"id": "hallucinated-reply-id", "kind": "fail", "check": "T6-003", "expect": "fail", "judge": "down",
     "families": ["multi_turn"], "user": "Update QX-2001.", "reply": "Updated QX-9999.",
     "read_result": '{"id": "QX-2001", "balance": 480}', "write_args": {"id": "QX-2001", "amount": 480}},
    {"id": "reply-amount-not-the-tool-amount", "kind": "fail", "check": "T6-002", "expect": "fail", "judge": "down",
     "families": ["multi_turn"], "user": "Update QX-2001.", "reply": "The balance is INR 1000.",
     "read_result": '{"id": "QX-2001", "balance": 100}', "write_args": {"id": "QX-2001", "amount": 100}},
    {"id": "reply-id-not-in-state", "kind": "fail", "check": "T6-003", "expect": "fail", "judge": "down",
     "families": ["multi_turn"], "user": "Update QX-2001.", "reply": "Updated QX-9999.",
     "initial": {"balance": 480}, "read_result": '{"id": "QX-2001", "balance": 480}',
     "write_args": {"id": "QX-2001", "amount": 480}},
]


def _agent(case: dict, vocab: dict) -> Agent:
    gov = dict(case.get("gov") or {})
    tools = {
        vocab["read"]: {"name": vocab["read"], "description": "Read one record.", "annotations": {"readOnlyHint": True, "destructiveHint": False}},
        vocab["write"]: {"name": vocab["write"], "description": "Record the decision.", "annotations": {"readOnlyHint": False, "destructiveHint": True}},
    }
    card = {"name": "unit-f8", "skills": [{"id": "s", "name": "s", "description": "s", "tags": ["en"]}],
            "capabilities": {"extensions": [{"uri": GOV_EXT, "params": gov}]}}
    return Agent("unit-f8", Path("/tmp/unit-f8"), card, tools, gov)


def _tools(case: dict, vocab: dict) -> list[ToolCall]:
    read_args = case.get("read_args", {"id": "QX-2001"})
    calls = [ToolCall(vocab["read"], read_args, result=case.get("read_result", '{"id": "QX-2001"}'))]
    if case.get("write_args") is not None:
        calls.append(ToolCall(vocab["write"], case["write_args"], result=case.get("write_result", "{}")))
    return calls


def _extra(case: dict) -> dict:
    extra = {}
    if case.get("lang"):
        extra["agentest.user.language"] = case["lang"]
    if case.get("families"):
        extra["agentest.input.families"] = list(case["families"])
    if case.get("initial") is not None:
        extra["agentest.initial_state"] = json.dumps(case["initial"])
    if case.get("policy") is not None:
        extra["agentest.language.policy"] = json.dumps(case["policy"])
    return extra


def _native(case: dict, vocab: dict):
    ep = Episode(agent="unit-f8", probe=case["id"], input=case["user"], final_answer=case["reply"], rep=0,
                 tool_calls=_tools(case, vocab), final_state=dict(case.get("initial") or {}))
    return from_otlp(to_otlp(ep, "unit-f8", _extra(case)))


def _langgraph(case: dict, vocab: dict):
    trace = [{"role": "human", "content": case["user"]}]
    for call in _tools(case, vocab):
        trace.append({"role": "ai", "content": "", "tool_calls": [{"name": call.name, "args": call.arguments}]})
        trace.append({"role": "tool", "content": call.result if isinstance(call.result, str) else json.dumps(call.result)})
    trace.append({"role": "ai", "content": case["reply"]})
    raw = {"probe": case["id"], "input": case["user"], "output": {"reply": case["reply"]}, "trace": trace, "attributes": _extra(case)}
    mapping = {"dialect": "langgraph_msgs", "framework": "LangGraph",
               "observations": {"final_answer": ["output.reply"]},
               "labels": {"inputs": {case["id"]: {"families": list(case.get("families") or [])}}}}
    docs = to_docs([raw], mapping, "unit-f8", is_write=lambda name: name == vocab["write"])
    return from_otlp(docs[0])


def _status(case: dict, vocab: dict, dialect: str) -> str:
    run = _native(case, vocab) if dialect == "otlp" else _langgraph(case, vocab)
    ctx = no_judge() if case["judge"] == "down" else stub_judge(lambda gid, _payload: {"lang": case["judge"], "langs": [case["judge"]]})
    with ctx:
        got = evaluate(_agent(case, vocab), [run], [case["check"]])
    return got[case["check"]].status


def test_registry_hook_uses_the_f8_detector():
    for tid in ("T6-010", "T6-002", "T6-003"):
        assert "f8.py" in RULES[tid][1].__code__.co_filename


def test_family_has_enough_positives_and_negatives_in_three_scripts():
    assert sum(c["kind"] == "pass" and c["expect"] == "pass" for c in CASES) >= 10
    assert sum(c["kind"] == "fail" for c in CASES) >= 10
    scripts = {dominant for case in CASES for dominant in (case["user"][:1],)}
    assert any("\u0c80" <= ch <= "\u0cff" for case in CASES for ch in case["user"])  # Kannada block
    assert any("\u0900" <= ch <= "\u097f" for case in CASES for ch in case["user"])  # Devanagari
    assert any("A" <= ch <= "z" for case in CASES for ch in case["user"])  # Latin
    assert scripts


def test_english_user_english_reply_passes():
    case = next(c for c in CASES if c["id"] == "en-en")
    assert _status(case, VOCABS["records"], "otlp") == "pass"


def test_kannada_latin_transliteration_follows_declared_policy():
    allowed = next(c for c in CASES if c["id"] == "kn-latn-allowed")
    denied = next(c for c in CASES if c["id"] == "kn-latn-denied")
    tagged = next(c for c in CASES if c["id"] == "kn-latn-tag")
    assert _status(allowed, VOCABS["records"], "otlp") == "pass"
    assert _status(denied, VOCABS["records"], "otlp") == "fail"
    assert _status(tagged, VOCABS["rows"], "langgraph") == "pass"


def test_judge_down_without_language_tag_is_not_assessed():
    case = next(c for c in CASES if c["id"] == "kn-latn-judge-down")
    assert case["judge"] == "down" and "lang" not in case
    got = _status(case, VOCABS["records"], "otlp")
    assert got == "not-assessed"
    assert got != "pass"


def test_hallucinated_amount_fails_and_bound_amount_passes():
    hallucinated = next(c for c in CASES if c["id"] == "hallucinated-reply-amount")
    bound_input = next(c for c in CASES if c["id"] == "amount-from-input")
    bound_tool = next(c for c in CASES if c["id"] == "amount-from-tool")
    assert _status(hallucinated, VOCABS["records"], "otlp") == "fail"
    assert _status(bound_input, VOCABS["rows"], "langgraph") == "pass"
    assert _status(bound_tool, VOCABS["records"], "langgraph") == "pass"


def test_results_agree_across_vocabularies_and_dialects():
    bad = []
    for case in CASES:
        got = {(name, dialect): _status(case, vocab, dialect) for name, vocab in VOCABS.items() for dialect in ("otlp", "langgraph")}
        if set(got.values()) != {case["expect"]}:
            bad.append((case["id"], case["expect"], got))
    assert not bad, bad
