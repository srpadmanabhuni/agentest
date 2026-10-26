"""Run the probes in ``probes.py`` against the vendored reference agents and
record episodes to ``fixtures/real/episodes/<agent>.jsonl``.

Needs the reference-agent dependencies (``reference_agents/requirements-reference.txt``)
and a local OpenAI-compatible model server on ``REF_LLM_BASE`` (default
``http://127.0.0.1:8008/v1``; see ``reference_agents/common/gguf_llm_server.py``).
Nothing here calls a hosted API. Usage::

    python -m agentest.real.live --agent a05 [--root /path/to/repo]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from agentest.real.probes import AGENT_DIRS, PROBES


def _sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def _jsonable(x: Any) -> Any:
    return json.loads(json.dumps(x, default=str))


def _load(ref: Path, key: str):
    d = ref / AGENT_DIRS[key]
    sys.path[:0] = [str(d), str(ref)]
    import importlib

    return importlib.import_module("agent"), d


def run_agent(key: str, ref: Path, probes: list[dict] | None = None) -> list[dict]:
    """Run ``probes`` (default: the first-41 set) against reference agent ``key`` and return episodes."""
    eps: list[dict] = []
    probes = PROBES[key] if probes is None else probes

    def rec(p: dict, rep: int, inp: Any, fn):
        t0 = time.time()
        try:
            out, trace, extra = fn()
            err = None
        except Exception as e:  # noqa: BLE001 - recorded, judged by checks
            out, trace, extra, err = None, [], {}, f"{type(e).__name__}: {e}"
        ep = {"agent": key, "probe": p["id"], "rep": rep, "input": inp, "output": out, "trace": trace,
              "extra": extra, "error": err, "elapsed_s": round(time.time() - t0, 1)}
        eps.append(_jsonable(ep))
        print(f"[{key}] {p['id']}#{rep} {ep['elapsed_s']}s err={err}", flush=True)

    if key == "a12":
        return _run_a12(ref, probes)
    if key == "a08":
        return _run_a08(ref, probes)
    mod, d = _load(ref, key)
    for p in probes:
        for rep in range(p.get("reps", 1)):
            if key == "a01":
                rec(p, rep, p["ticket"], lambda: (*mod.route(p["ticket"]), {}))
            elif key == "a02":
                rec(p, rep, p["msg"], lambda: (*mod.classify(p["msg"]), {}))
            elif key == "a03":
                rec(p, rep, p["q"], lambda: (*mod.ask(p["q"]), {}))
            elif key == "a04":
                rec(p, rep, [p["brief"], p["decision"]], lambda: (*mod.run(p["brief"], p["decision"]), {}))
            elif key == "a05":
                def f5():
                    out, tr = mod.run(p["msg"])
                    extra = {"refunded_before_human": list(mod.REFUNDED)}
                    if p.get("human_approve") and mod.PENDING:
                        oid = mod.PENDING[0]["order_id"]
                        extra["human_approved"] = mod.approve_refund(oid, p["human_approve"])
                        extra["refunded_after_human"] = list(mod.REFUNDED)
                    extra["agents"] = {a.name: [t.name for t in a.tools] for a in (mod.triage, mod.billing, mod.faq)}
                    return out, tr, extra
                rec(p, rep, p["msg"], f5)
            elif key == "a06":
                rec(p, rep, [p["req"], p["decision"]], lambda: (*mod.run(p["req"], p["decision"]), {}))
            elif key == "a07":
                db = d / "enterprise.db"
                if not db.exists():  # build the fixture DB first so the first probe has a 'before' hash
                    subprocess.run([sys.executable, "-c", "import mcp_server"], cwd=d, check=True)
                def f7():
                    h0 = _sha(db)
                    out, tr = mod.run(p["q"])
                    return out, tr, {"db_sha_before": h0, "db_sha_after": _sha(db)}
                rec(p, rep, p["q"], f7)
            elif key == "a09":
                rec(p, rep, p["topic"], lambda: (*mod.run(p["topic"]), {"corpus_urls": [c["url"] for c in mod.CORPUS]}))
            elif key == "a10":
                rec(p, rep, p["task"], lambda: (*mod.run(p["task"]), {}))
            elif key == "a11":
                rec(p, rep, p["req"], lambda: (*mod.run(p["req"]), {}))
    return eps


def _run_a12(ref: Path, probes: list[dict]) -> list[dict]:
    d = ref / AGENT_DIRS["a12"]
    tmp = Path(tempfile.mkdtemp(prefix="a12probe_"))
    env = {**os.environ, "A12_CKPT": str(tmp / "ckpt.sqlite"), "A12_LEDGER": str(tmp / "ledger.sqlite"), "PYTHONPATH": str(ref)}

    def step(*a):
        r = subprocess.run([sys.executable, str(d / "step.py"), *a], capture_output=True, text=True, cwd=d, env=env, timeout=600)
        lines = [ln for ln in r.stdout.splitlines() if ln.startswith("{")]
        if not lines:
            raise RuntimeError(r.stderr[-800:])
        return json.loads(lines[-1])

    def rows():
        import sqlite3
        if not (tmp / "ledger.sqlite").exists():
            return []
        c = sqlite3.connect(tmp / "ledger.sqlite")
        try:
            return [list(r) for r in c.execute("SELECT invoice_no, vendor, amount, approver FROM payments")]
        except sqlite3.OperationalError:
            return []

    eps = []
    for i, p in enumerate(probes):
        t0 = time.time()
        tid = f"probe-{i}-{p['id']}"
        err, out, trace = None, {}, []
        before = rows()
        try:
            s1 = step("start", tid, p["text"])
            trace.append({"process": 1, **s1})
            out = {"paused_after_start": bool(s1["paused_at"]), "result_after_start": s1["result"], "invoice": s1["invoice"]}
            if s1["paused_at"]:
                inv = s1["invoice"] or {}
                reply = p["reply"]
                if reply == "exact":
                    reply = {"approver": "finance-head", "token": f"APPROVE {inv.get('invoice_no')} {inv.get('amount')}"}
                if p.get("twin"):  # T1-017: two concurrent resumes of the same thread
                    import concurrent.futures as cf
                    with cf.ThreadPoolExecutor(2) as ex:
                        futs = [ex.submit(step, "resume", tid, json.dumps(reply)) for _ in range(2)]
                        twins = []
                        for f in futs:
                            try:
                                twins.append(f.result())
                            except Exception as e:  # noqa: BLE001
                                twins.append({"result": None, "invoice": None, "log": [], "error": str(e)[:300]})
                    s2 = twins[0]
                    out["twin_results"] = [t.get("result") for t in twins]
                else:
                    s2 = step("resume", tid, json.dumps(reply))
                trace.append({"process": 2, "human_reply": reply, **s2})
                out.update({"human_reply": reply, "result": s2["result"], "invoice_after_resume": s2["invoice"], "log": s2["log"]})
            else:
                out.update({"result": s1["result"], "log": s1["log"]})
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        ep = {"agent": "a12", "probe": p["id"], "rep": 0, "input": p["text"], "output": out, "trace": trace,
              "extra": {"ledger_before": before, "ledger_after": rows()}, "error": err, "elapsed_s": round(time.time() - t0, 1)}
        eps.append(_jsonable(ep))
        print(f"[a12] {p['id']} {ep['elapsed_s']}s err={err}", flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return eps


def _run_a08(ref: Path, probes: list[dict]) -> list[dict]:
    """One n8n execution with the probe questions injected into a COPY of the workflow."""
    d = ref / AGENT_DIRS["a08"]
    n8n = os.environ.get("N8N_DIR", "/workspace/n8n")
    env = {**os.environ, "N8N_USER_FOLDER": os.path.join(n8n, "home"), "N8N_DIAGNOSTICS_ENABLED": "false"}
    wf = json.loads((d / "workflow.n8n.json").read_text(encoding="utf-8"))
    wf["id"] = "AgentestA08Probe1"
    wf["name"] = "agentest A8 probes"
    items = [{"json": {"chatInput": p["q"], "sessionId": p["session"]}} for p in probes]
    for n in wf["nodes"]:
        if n["name"] == "Sample questions":
            n["parameters"]["jsCode"] = "return " + json.dumps(items) + ";"
    tmp = Path(tempfile.mkdtemp(prefix="a08probe_"))
    (tmp / "wf.json").write_text(json.dumps(wf))
    t0 = time.time()
    srv = subprocess.Popen([sys.executable, str(d / "mcp_http_server.py")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(4)
    try:
        for args in (["import:credentials", f"--input={d}/credentials.local.json"], ["import:workflow", f"--input={tmp}/wf.json"]):
            subprocess.run(["npx", "n8n", *args], cwd=n8n, env=env, capture_output=True, check=True)
        r = subprocess.run(["npx", "n8n", "execute", "--id", wf["id"], "--rawOutput"], cwd=n8n, env=env, capture_output=True, text=True, timeout=3000)
    finally:
        srv.terminate()
    s = r.stdout
    data = json.loads(s[s.find("\n{") + 1:])
    rd = data["data"]["resultData"]["runData"]
    outs = [i["json"].get("output") for i in rd["AI Agent"][0]["data"]["main"][0]]
    tool_runs = rd.get("MCP Client (helpdesk)", [])
    tools = []
    for run in tool_runs:
        for x in run["data"]["ai_tool"][0]:
            tools.append(x["json"])
    tool_names = [t.get("tool") or t.get("name") for run in tool_runs for t in [run.get("inputOverride", {}).get("ai_tool", [[{}]])[0][0].get("json", {})]]
    el = round(time.time() - t0, 1)
    eps = []
    for p, o in zip(probes, outs):
        eps.append(_jsonable({"agent": "a08", "probe": p["id"], "rep": 0, "input": {"q": p["q"], "session": p["session"]}, "output": {"output": o},
                              "trace": [], "extra": {"n8n_status": data.get("status"), "tool_results_whole_run": tools, "tool_inputs_whole_run": tool_names},
                              "error": None, "elapsed_s": el}))
    shutil.rmtree(tmp, ignore_errors=True)
    return eps


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; returns the process exit code."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True, choices=sorted(PROBES))
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--set", default="", help="extra probe set from probes2 (e.g. b1); default = first-41 probes")
    a = ap.parse_args(argv)
    root = Path(a.root)
    probes = None
    if a.set:
        from agentest.real.probes2 import sets
        probes = sets()[a.set].get(a.agent, [])
        if not probes:
            print(f"no {a.set} probes for {a.agent}")
            return 0
    eps = run_agent(a.agent, root / "reference_agents", probes)
    out = root / "fixtures" / "real" / "episodes" / (f"{a.agent}.{a.set}.jsonl" if a.set else f"{a.agent}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for e in eps:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"wrote {len(eps)} episodes -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
