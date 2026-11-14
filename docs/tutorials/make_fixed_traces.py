#!/usr/bin/env python3
"""Make "fixed" copies of selected scenarios from the bundled `eager` sample agent.

Used by the three tutorials in docs/tutorials/. It reads agents/eager/traces/eager.otlp.jsonl, keeps only the
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


def fix_state(cid, text):
    """Edit the recorded final state (a JSON string) the way a corrected agent would have behaved."""
    if cid == "T6-003":  # tutorial 3: keep the same ticket for the whole conversation
        return text.replace("T-OTHER", "T-9")
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
