"""Generic defect injection (v4.0 r10 self-test): take clean traces, inject one known defect, and check that the
rules catch it. The mutators read only the trace structure (state-changing calls by the agent's tool annotations,
decision-like argument names, dates and numbers in the text); no agent, tool or domain name is assumed.

Mutations: flip-decision, repeat-write, drop-disclosure, shift-date, garble-reply. Each returns a mutated deep copy
of one run, or None when the run offers nothing to mutate."""

from __future__ import annotations

import copy
import datetime as _dt
import json
import re
from collections.abc import Callable

DECISION_KEYS = {"decision", "outcome", "verdict", "action", "status", "result"}
FAVOURABLE = {"approve": "reject", "approved": "rejected", "accept": "decline", "accepted": "declined", "release": "reject",
              "released": "rejected", "refund": "reject", "pay": "reject", "allow": "deny", "allowed": "denied", "grant": "deny",
              "granted": "denied"}
ADVERSE = {v: k for k, v in FAVOURABLE.items()}
ISO_RX = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")  # rx: format
SENT_RX = re.compile(r"(?<=[.!?।])\s+")  # rx: format
NUM_RX = re.compile(r"\d[\d,]*(?:\.\d+)?")  # rx: format


def _writes(agent, run):
    return [i for i, t in enumerate(run.tools) if agent.is_write(t.name) and not t.error]


def flip_decision(agent, run):
    """A successful state-changing call records the opposite decision; the reply is unchanged."""
    for i in _writes(agent, run):
        for k, v in (run.tools[i].args or {}).items():
            if k.lower() in DECISION_KEYS and isinstance(v, str) and v.lower() in {**FAVOURABLE, **ADVERSE}:
                r = copy.deepcopy(run)
                new = {**FAVOURABLE, **ADVERSE}[v.lower()]
                r.tools[i].args[k] = new
                r.tools[i].result = r.tools[i].result.replace(json.dumps(v), json.dumps(new))
                for e in r.effects:
                    if e.get("effect") == r.tools[i].name and isinstance(e.get("data"), dict) and k in e["data"]:
                        e["data"] = {**e["data"], k: new}
                return r
    return None


def repeat_write(agent, run):
    """The first successful state-changing call is issued a second time with the same arguments."""
    w = _writes(agent, run)
    if not w:
        return None
    r = copy.deepcopy(run)
    t = copy.deepcopy(r.tools[w[0]])
    t.t = max(x.t for x in r.tools) + 1
    t.call_id = (t.call_id or "c") + "-again"
    r.tools.append(t)
    prev = [e for e in r.effects if e.get("effect") == t.name and e.get("kind") == "executed"]
    if prev:  # the trace records effects: the repeated call has one too (same shape, later time)
        e = copy.deepcopy(prev[0])
        e["t"] = t.t
        r.effects.append(e)
    return r


def drop_disclosure(agent, run):
    """Remove from the reply the sentences that carry a required disclosure: the value of a held-back field a read
    result gives (locked, withheld, deducted ... ) or the contest / grievance route; the rest of the reply stays."""
    from agentest.standards.rules import HELD_PARTS, ROUTE_PARTS, _json_obj, _name_parts

    held = set()
    for t in run.tools:
        o = _json_obj(t.result) if not agent.is_write(t.name) else None
        if isinstance(o, dict):
            held |= {str(v) for k, v in o.items() if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
                     and set(_name_parts(str(k))) & HELD_PARTS}

    def carries(s):
        low = s.lower()
        return bool({n.replace(",", "") for n in NUM_RX.findall(s)} & held) or any(w in low for w in ROUTE_PARTS)

    sents = SENT_RX.split((run.answer or "").strip())
    keep = [s for s in sents if not carries(s)]
    if not keep or len(keep) == len(sents):
        return None
    r = copy.deepcopy(run)
    r.answer = " ".join(keep)
    return r


def shift_date(agent, run):
    """An ISO date in the reply is moved one week later (a date no tool gave)."""
    m = ISO_RX.search(run.answer or "")
    if not m:
        return None
    d = _dt.date(int(m[1]), int(m[2]), int(m[3])) + _dt.timedelta(days=7)
    r = copy.deepcopy(run)
    r.answer = r.answer[:m.start()] + d.isoformat() + r.answer[m.end():]
    return r


def garble_reply(agent, run):
    """A non-Latin-script reply falls into a decoding loop (its first clause repeated three times)."""
    a = run.answer or ""
    if sum(ch.isalpha() and not ch.isascii() for ch in a) < 10:
        return None
    words = a.split()
    if len(words) < 5:
        return None
    clause = " ".join(words[:5])
    r = copy.deepcopy(run)
    r.answer = " ".join([clause] * 3) + " " + a
    return r


MUTATIONS: dict[str, Callable] = {"flip-decision": flip_decision, "repeat-write": repeat_write,
                                  "drop-disclosure": drop_disclosure, "shift-date": shift_date, "garble-reply": garble_reply}


def self_test(agent, runs, ids=None, mode: str = "examples") -> dict:
    """For each mutation: inject it into the first run it applies to, and report the checks that pass (or n/a) on the
    clean traces but fail on the mutated ones. {mutation: {"run": id, "caught_by": [...]} or None (not applicable)}."""
    from agentest.standards.rules import evaluate

    base = evaluate(agent, runs, ids=ids, mode=mode)
    out: dict = {}
    for name, fn in MUTATIONS.items():
        out[name] = None
        for k, run in enumerate(runs):
            m = fn(agent, run)
            if m is None:
                continue
            got = evaluate(agent, runs[:k] + [m] + runs[k + 1:], ids=ids, mode=mode)
            caught = sorted(i for i, v in got.items() if v.status == "fail" and base[i].status != "fail")
            out[name] = {"run": run.input_id, "caught_by": caught}
            break
    return out
