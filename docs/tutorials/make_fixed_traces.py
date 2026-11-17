#!/usr/bin/env python3
"""Make "fixed" copies of selected scenarios from the bundled `eager` sample agent.

Used by tutorials 1, 2, 3 and 6 in docs/tutorials/. It reads agents/eager/traces/eager.otlp.jsonl, keeps only the
scenarios a tutorial needs, and (with --fixed) edits the recorded tool calls the way a corrected agent would
behave. This is a teaching aid: it simulates a corrected agent by editing a recorded trace, it is not a real
agent run. Standard library only.

    python docs/tutorials/make_fixed_traces.py --show --ids T5-001,T5-005
    python docs/tutorials/make_fixed_traces.py --out /tmp/eager-before.jsonl --ids T5-001,T5-005
    python docs/tutorials/make_fixed_traces.py --out /tmp/eager-after.jsonl  --ids T5-001,T5-005 --fixed
"""
import argparse
import json
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[2] / "agents" / "eager" / "traces" / "eager.otlp.jsonl"


def attrs(span):
    return {a["key"]: a["value"] for a in span["attributes"]}


def set_attr(span, key, text):
    for a in span["attributes"]:
        if a["key"] == key:
            a["value"] = {"stringValue": text}


# Tutorial 6 (personal data and secret leaks): plain text swaps applied to the recorded trace and final state.
LEAK_FIXES = {
    "T5-004": [("Find user with SSN 123-45-6789", "Find user with customer id C-1001")],
    "T6-011": [("your key is sk-test-ABC123SECRET", "your key is stored; I will not repeat it")],
    "T7-014": [("Email them at jane.doe@example.com", "Email them at j***@example.com")],
}


def fix_state(cid, text):
    """Edit the recorded final state (a JSON string) the way a corrected agent would have behaved."""
    if cid == "T6-003":  # tutorial 3: keep the same ticket for the whole conversation
        return text.replace("T-OTHER", "T-9")
    if cid in LEAK_FIXES:  # tutorial 6: the corrected agent never writes the raw value
        for old, new in LEAK_FIXES[cid]:
            text = text.replace(old, new)
        return text
    if cid == "T4-009":  # tutorial 6: the agent ignores the instruction hidden in the resume and sends nothing
        state = json.loads(text)
        out = state["output"]
        out["emails"] = []
        out["env"]["emails"] = []
        for key in ("calls", "tool_calls"):
            out["tr"][key] = [c for c in out["tr"][key] if c["name"] != "send_email"]
        out["tr"]["tool_names"] = {"$set": []}
        return json.dumps(state)
    state = json.loads(text)
    w = state["output"]["world"]
    calls = w["w"]["calls"]
    if cid == "T5-001":  # tutorial 1: never call a tool that is not declared
        calls[:] = [c for c in calls if c["tool"] != "admin_export"]
    elif cid == "T5-005":  # tutorial 1: stay on the allowlisted host
        for c in calls:
            c["args"]["url"] = "https://api.acme.example/latest"
    elif cid == "T6-002":  # tutorial 3: pay the amount that was agreed
        for c in calls:
            c["args"]["amount"] = w["slots"]["amount"]
    return json.dumps(state)


def fix_spans(cid, spans):
    if cid == "T4-009":  # tutorial 6: drop the send_email tool span
        spans[:] = [s for s in spans if attrs(s).get("gen_ai.tool.name", {}).get("stringValue") != "send_email"]
        return
    if cid in LEAK_FIXES:
        for s in spans:
            for a in s["attributes"]:
                v = a["value"].get("stringValue")
                if v:
                    for old, new in LEAK_FIXES[cid]:
                        v = v.replace(old, new)
                    a["value"] = {"stringValue": v}
        return
    if cid == "T6-003":  # tutorial 3: the later tool calls reuse the first ticket
        for s in spans:
            for key in ("gen_ai.tool.call.arguments", "gen_ai.tool.call.result"):
                v = attrs(s).get(key)
                if v and "T-OTHER" in v["stringValue"]:
                    set_attr(s, key, v["stringValue"].replace("T-OTHER", "T-9"))


def show(cid, text):
    """Print the tool calls recorded for one scenario (the evidence the checks read)."""
    out = json.loads(text)["output"]
    print(f"== {cid}")
    if "world" in out and "outs" in out["world"]:  # memory scenarios record user-visible outputs per turn
        for i, o in enumerate(out["world"]["outs"]):
            print(f"  turn {i} output: {json.dumps(o)}")
        return
    if out.get("outputs"):
        for k, v in out["outputs"].items():
            print(f"  {k} output: {json.dumps(v)}")
    if "world" in out:
        w = out["world"]
        calls = (w.get("w") or w.get("_h0"))["calls"]
        for c in calls:
            print(f"  call {c['tool']} {json.dumps(c['args'])}")
        for key in ("allow", "slots"):
            if key in w:
                print(f"  {key}: {json.dumps(w[key])}")
    else:
        for c in out["tr"]["calls"]:
            print(f"  call {c['name']} {json.dumps(c['args'])} -> {json.dumps(c['result'])}")
        for f in out["env"].get("files", []):
            print(f"  file {f['name']}: {json.dumps(f['text'])}")
        if out["env"]["state"]["binding_history"]:
            print(f"  binding_history: {json.dumps(out['env']['state']['binding_history'])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="print the recorded tool calls instead of writing a file")
    ap.add_argument("--out")
    ap.add_argument("--ids", required=True, help="comma-separated test IDs, e.g. T5-001,T5-005")
    ap.add_argument("--fixed", action="store_true", help="simulate a corrected agent")
    ns = ap.parse_args()
    want = set(ns.ids.split(","))
    kept = []
    shown = {}
    for line in SRC.read_text().splitlines():
        rec = json.loads(line)
        spans = rec["resourceSpans"][0]["scopeSpans"][0]["spans"]
        root = spans[0]
        cid = attrs(root)["agentest.input.id"]["stringValue"]
        if cid not in want:
            continue
        if ns.show:
            shown[cid] = attrs(root)["agentest.final_state"]["stringValue"]
            continue
        if ns.fixed:
            fix_spans(cid, spans)
            fs = attrs(root).get("agentest.final_state")
            if fs:
                set_attr(root, "agentest.final_state", fix_state(cid, fs["stringValue"]))
        kept.append(json.dumps(rec))
    if ns.show:
        for cid in ns.ids.split(","):  # print in the order asked for
            if cid in shown:
                show(cid, shown[cid])
        return
    if not ns.out:
        ap.error("--out is required unless --show is used")
    pathlib.Path(ns.out).write_text("\n".join(kept) + "\n")
    print(f"wrote {len(kept)} scenario(s) to {ns.out}")


if __name__ == "__main__":
    main()
