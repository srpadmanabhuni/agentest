"""Harness-signed traces and intercepted-traffic cross-checks (v4.0-trust). Stdlib only (hashlib, hmac).

Threat model: the agent (its model and any code it controls) may write anything into its own messages, log lines,
span attributes and success / approval flags. Only the harness - the recorder or proxy that executes the tools and
holds a key the agent never sees - is trusted. A trace is *attested* when

1. its spans form a SHA-256 hash chain whose head is HMAC-SHA256-signed with the harness key
   (resource attributes ``agentest.trace.chain`` / ``agentest.trace.hmac`` / ``agentest.trace.key_id``), and
2. every ``execute_tool`` span matches one record of the harness's intercepted tool traffic (``traffic/*.jsonl`` next
   to the traces; one HMAC-signed line per executed call: trace id, call id, tool, SHA-256 of the canonical arguments and
   of the result) and every intercepted call has its span - a claimed but unseen call is forged, an unreported call is
   hidden.

The key comes from ``$AGENTEST_TRACE_KEY_FILE`` (a file path) or ``$AGENTEST_TRACE_KEY``; it is read by the recorder /
proxy and by the verifier, never passed to the agent. Nothing here names an agent.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

SIG_KEYS = ("agentest.trace.chain", "agentest.trace.hmac", "agentest.trace.key_id", "agentest.trace.alg")
ALG = "sha256-chain+hmac-sha256/v1"
GENESIS = "0" * 64


def load_key(path: str | None = None) -> bytes | None:
    """The harness key: an explicit file, else $AGENTEST_TRACE_KEY_FILE, else $AGENTEST_TRACE_KEY; None when unset."""
    p = path or os.environ.get("AGENTEST_TRACE_KEY_FILE")
    if p:
        return Path(p).read_bytes().strip()
    k = os.environ.get("AGENTEST_TRACE_KEY")
    return k.encode() if k else None


def key_id(key: bytes) -> str:
    return hashlib.sha256(b"agentest-key-id:" + key).hexdigest()[:16]


def _c(x) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _canon_span(s: dict) -> str:
    """A span independent of attribute / event order (collectors may reorder lists)."""
    d = dict(s)
    d["attributes"] = sorted(s.get("attributes") or [], key=lambda a: a.get("key", ""))
    d["events"] = sorted(({**e, "attributes": sorted(e.get("attributes") or [], key=lambda a: a.get("key", ""))} for e in s.get("events") or []),
                         key=lambda e: (str(e.get("timeUnixNano", "")), e.get("name", ""), _c(e.get("attributes"))))
    return _c(d)


def _spans(doc: dict) -> list[dict]:
    return [s for rs in doc.get("resourceSpans", []) for ss in rs.get("scopeSpans", []) for s in ss.get("spans", [])]


def _resource_attrs(doc: dict) -> list[dict]:
    return [a for rs in doc.get("resourceSpans", []) for a in (rs.get("resource") or {}).get("attributes", []) if a.get("key") not in SIG_KEYS]


def chain(doc: dict) -> str:
    """Hash chain over the resource attributes (minus the signature) and every span, ordered by span id."""
    h = hashlib.sha256((GENESIS + _c(sorted(_resource_attrs(doc), key=lambda a: a.get("key", "")))).encode()).hexdigest()
    for s in sorted(_spans(doc), key=lambda s: (s.get("traceId", ""), s.get("spanId", ""))):
        h = hashlib.sha256((h + _canon_span(s)).encode()).hexdigest()
    return h


def _sig_attrs(doc: dict) -> dict:
    out = {}
    for rs in doc.get("resourceSpans", []):
        for a in (rs.get("resource") or {}).get("attributes", []):
            if a.get("key") in SIG_KEYS:
                out[a["key"]] = (a.get("value") or {}).get("stringValue", "")
    return out


def sign(doc: dict, key: bytes) -> dict:
    """Sign one OTLP/JSON document in place (harness side) and return it."""
    for rs in doc.get("resourceSpans", []):
        res = rs.setdefault("resource", {})
        res["attributes"] = [a for a in res.get("attributes", []) if a.get("key") not in SIG_KEYS]
    h = chain(doc)
    sig = {"agentest.trace.chain": h, "agentest.trace.hmac": hmac.new(key, h.encode(), hashlib.sha256).hexdigest(),
           "agentest.trace.key_id": key_id(key), "agentest.trace.alg": ALG}
    rs0 = doc["resourceSpans"][0].setdefault("resource", {})
    rs0.setdefault("attributes", []).extend({"key": k, "value": {"stringValue": v}} for k, v in sig.items())
    return doc


def verify(doc: dict, key: bytes | None) -> tuple[str, str]:
    """('signed' | 'unsigned' | 'bad-signature' | 'no-key', detail)."""
    sig = _sig_attrs(doc)
    if not sig.get("agentest.trace.hmac"):
        return "unsigned", "no harness signature"
    if key is None:
        return "no-key", "signed, but no harness key to verify with ($AGENTEST_TRACE_KEY_FILE)"
    if sig.get("agentest.trace.key_id") != key_id(key):
        return "bad-signature", "signed with a different key"
    h = chain(doc)
    if h != sig.get("agentest.trace.chain"):
        return "bad-signature", "hash chain does not match the spans (trace edited after signing)"
    if not hmac.compare_digest(hmac.new(key, h.encode(), hashlib.sha256).hexdigest(), sig.get("agentest.trace.hmac", "")):
        return "bad-signature", "HMAC does not match"
    return "signed", "hash chain and harness HMAC verified"


# ------------------------------------------------------------------ intercepted tool traffic

def args_hash(args) -> str:
    if isinstance(args, str):
        try:
            args = json.loads(args or "{}")
        except ValueError:
            pass
    return hashlib.sha256(_c(args).encode()).hexdigest()


def result_hash(result) -> str:
    return hashlib.sha256((result if isinstance(result, str) else _c(result)).encode()).hexdigest()


def traffic_record(key: bytes, trace_id: str, call_id: str, tool: str, args, result: str) -> dict:
    """One intercepted tool call (written by the harness proxy / recorder at execution time)."""
    rec = {"trace_id": trace_id, "call_id": call_id, "tool": tool, "args_sha256": args_hash(args), "result_sha256": result_hash(result)}
    rec["hmac"] = hmac.new(key, _c(rec).encode(), hashlib.sha256).hexdigest()
    return rec


def read_traffic(paths) -> list[dict]:
    out = []
    for p in paths:
        for ln in Path(p).read_text().splitlines():
            if ln.strip():
                out.append(json.loads(ln))
    return out


def _attr(s: dict, k: str):
    for a in s.get("attributes", []):
        if a.get("key") == k:
            v = a.get("value") or {}
            return next(iter(v.values()), None) if v else None
    return None


def cross_check(doc: dict, traffic: list[dict], key: bytes | None) -> list[str]:
    """Problems between the execute_tool spans of one trace and the intercepted traffic ([] = consistent)."""
    tids = {s.get("traceId", "") for s in _spans(doc)}
    recs, bad = {}, []
    for r in traffic:
        if r.get("trace_id") not in tids:
            continue
        body = {k: v for k, v in r.items() if k != "hmac"}
        if key is None or not hmac.compare_digest(hmac.new(key, _c(body).encode(), hashlib.sha256).hexdigest(), str(r.get("hmac", ""))):
            bad.append(f"traffic record {r.get('call_id')!r} not signed by the harness")
            continue
        recs[r["call_id"]] = r
    seen = set()
    for s in _spans(doc):
        if _attr(s, "gen_ai.operation.name") != "execute_tool":
            continue
        cid, tool = str(_attr(s, "gen_ai.tool.call.id") or ""), str(_attr(s, "gen_ai.tool.name") or "")
        r = recs.get(cid)
        if not cid or r is None:
            bad.append(f"forged call: span {tool}#{cid or '?'} has no intercepted tool traffic")
            continue
        seen.add(cid)
        if r["tool"] != tool:
            bad.append(f"forged call {cid}: span says {tool}, traffic says {r['tool']}")
        if r["args_sha256"] != args_hash(_attr(s, "gen_ai.tool.call.arguments") or "{}"):
            bad.append(f"forged call {cid}: arguments differ from the intercepted call")
        if r["result_sha256"] != result_hash(str(_attr(s, "gen_ai.tool.call.result") or "")):
            bad.append(f"forged call {cid}: result differs from the intercepted call")
    bad += [f"hidden call: intercepted {r['tool']}#{c} has no span" for c, r in recs.items() if c not in seen]
    return bad


def has_message_only_calls(doc: dict) -> bool:
    """Tool calls that exist only as tool_call parts of model messages (no execute_tool span recorded them)."""
    sp = _spans(doc)
    if any(_attr(s, "gen_ai.operation.name") == "execute_tool" for s in sp):
        return False
    for s in sp:
        for k in ("gen_ai.output.messages", "gen_ai.input.messages"):
            v = _attr(s, k)
            if isinstance(v, str) and '"tool_call"' in v:
                return True
    return False


def assess(doc: dict, traffic: list[dict] | None, key: bytes | None) -> dict:
    """Evidence status of one trace: signature, traffic cross-check, message-only (reconstructed) tool calls."""
    st, why = verify(doc, key)
    xc = cross_check(doc, traffic, key) if traffic is not None else None
    derived = has_message_only_calls(doc)
    problems = []
    if st != "signed":
        problems.append(f"{st}: {why}")
    if xc is None:
        problems.append("no intercepted tool traffic")
    else:
        problems += xc
    if derived:
        problems.append("tool calls reconstructed from model messages (no execute_tool span): self-reported by the model")
    forged = st == "bad-signature" or bool(xc) or derived
    return {"signature": st, "traffic": "missing" if xc is None else ("ok" if not xc else "mismatch"), "derived_calls": derived,
            "attested": st == "signed" and xc == [] and not derived, "forged": forged, "problems": problems}


# ------------------------------------------------------------------ evidence labels and result trust

EVIDENCE_KINDS = ("harness", "reply", "self_report", "judge")


def evidence_table() -> dict[str, list[str]]:
    return json.loads((Path(__file__).with_name("evidence.json")).read_text())["rules"]


def evidence_of(tid: str) -> list[str]:
    """Evidence labels of one check; an unlabelled (user plugin) rule is treated as self_report until labelled."""
    return evidence_table().get(tid) or ["self_report"]


def traffic_files(adir: Path) -> list[Path]:
    return sorted(adir.glob("traffic/*.jsonl")) + sorted(adir.glob("*.traffic.jsonl"))


def assess_agent(docs: list[dict], adir: Path, key: bytes | None) -> dict:
    tf = traffic_files(adir)
    traffic = read_traffic(tf) if tf else None
    per = [assess(d, traffic, key) for d in docs]
    return {"traces": len(per), "signed": sum(p["signature"] == "signed" for p in per),
            "attested": bool(per) and all(p["attested"] for p in per), "forged": any(p["forged"] for p in per),
            "derived_calls": any(p["derived_calls"] for p in per),
            "unsigned": sum(p["signature"] != "signed" for p in per),
            "problems": sorted({x for p in per for x in p["problems"]})}


def trust_of(tid: str, ag: dict) -> tuple[str, str]:
    """high: attested trace (signed hash chain + every tool call seen in intercepted traffic); medium: unattested trace,
    check reads no self-reported field and no reconstructed calls; low: anything self-reported or reconstructed without
    attestation, or a forged trace."""
    ev = evidence_of(tid)
    if ag["forged"] and not ag["derived_calls"]:
        return "low", "trace failed signature or traffic cross-check"
    if ag["attested"]:
        return "high", "attested trace"
    if ag["derived_calls"]:
        return "low", "tool calls reconstructed from model messages"
    if "self_report" in ev:
        return "low", "uncorroborated self-report on an unattested trace"
    return "medium", "unattested trace (unsigned or no intercepted traffic)"


def annotate(res: dict, assessments: dict[str, dict], blind: bool = False) -> dict:
    """Attach evidence + trust to every result (json form). Blind mode: a forged or reconstructed trace passes nothing."""
    from agentest.standards.expr import R

    for a, row in res.items():
        ag = assessments[a]
        for tid, r in list(row.items()):
            t, why = trust_of(tid, ag)
            if blind and (ag["forged"] or not ag["attested"]) and r.status not in ("n/a", "not-run"):
                r = row[tid] = R("fail", "untrusted trace in blind mode: " + "; ".join(ag["problems"][:3]))
            r.evidence, r.trust, r.trust_reason = evidence_of(tid), t, why
    return res


def blind_counts(res_json: dict) -> dict:
    """Fail cells that count toward blind precision / recall: high trust only (low / medium excluded)."""
    out = {"high": 0, "medium": 0, "low": 0}
    for row in res_json.values():
        for c in row.values():
            if c["status"] == "fail":
                out[c.get("trust", "low")] += 1
    return out
