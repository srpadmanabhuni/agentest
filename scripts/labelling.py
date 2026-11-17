"""Contributor labelling: hand out batches of 10 fresh traces, collect labels from two independent labellers per trace,
resolve disagreements, and write a lock manifest with a hash BEFORE any predictions run.

    python scripts/labelling.py batch --labeller YOUR_GITHUB_HANDLE        # writes labelling-batch-<handle>-<id>.json
    python scripts/labelling.py submit labelling-batch-<handle>-<id>.json  # validates, writes labelling/labels/<handle>--<id>.json
    python scripts/labelling.py status                                     # counts only (no labels are shown)
    python scripts/labelling.py collect                                    # maintainer: agreements, and the disagreements to resolve
    python scripts/labelling.py lock                                       # maintainer: write labelling/LOCK.json (immutable)
    python scripts/labelling.py verify [--predictions FILE]                # anyone: recompute the hash; refuse on mismatch

Rubric and rules: docs/contributing/LABELLING.md. This script never runs a check and never reads a prediction for any
purpose except to compare the lock hash it carries. Deterministic and offline; standard library plus agentest's rule text.
"""
# Ref: internal design (docs/contributing/LABELLING.md); no external source.
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELLING = ROOT / "labelling"
VALID = ("pass", "fail", "n/a")
HANDLE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
SCHEMA_BATCH, SCHEMA_LABELS, SCHEMA_LOCK = "agentest-label-batch/1", "agentest-labels/1", "agentest-label-lock/1"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dirs(base: Path | None) -> tuple[Path, Path, Path]:
    b = Path(base) if base else LABELLING
    return b / "pool", b / "labels", b / "resolutions"


def load_pool(base: Path | None = None) -> dict[str, dict]:
    pool_dir, _, _ = _dirs(base)
    pool = {}
    for p in sorted(pool_dir.glob("LT-*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("schema") != "agentest-label-trace/1" or d.get("id") != p.stem or not d.get("checks") or not d.get("turns"):
            raise SystemExit(f"{p.name}: not a valid label trace")
        if any(k in d for k in ("label", "labels", "expected", "verdict")):
            raise SystemExit(f"{p.name}: a pool trace must not carry labels")
        pool[d["id"]] = d
    return pool


def load_labels(base: Path | None = None) -> list[dict]:
    _, labels_dir, _ = _dirs(base)
    out = []
    for p in sorted(labels_dir.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("schema") != SCHEMA_LABELS:
            raise SystemExit(f"{p.name}: not a labels file")
        d["_file"] = p.name
        out.append(d)
    return out


def rule_text(check: str) -> str:
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from agentest.standards.rules import RULES
        return RULES[check][0]
    except Exception:  # the rule text is a convenience; the batch is still valid without it
        return ""


def labelled_by(labels: list[dict]) -> dict[str, set[str]]:
    seen: dict[str, set[str]] = {}
    for f in labels:
        for x in f["labels"]:
            seen.setdefault(x["trace_id"], set()).add(f["labeller"])
    return seen


# ---------------------------------------------------------------- batch / submit

def make_batch(labeller: str, size: int = 10, base: Path | None = None) -> dict:
    if not HANDLE.match(labeller):
        raise SystemExit("--labeller must be your GitHub handle (letters, digits and hyphens)")
    pool, labels = load_pool(base), load_labels(base)
    seen = labelled_by(labels)
    todo = [t for t in pool if labeller not in seen.get(t, set()) and len(seen.get(t, set())) < 2]
    # finish pairs first (traces with one label), then fresh traces; stable per labeller so two people get different orders
    todo.sort(key=lambda t: (-len(seen.get(t, set())), sha256_bytes(f"{labeller}:{t}".encode())))
    chosen = sorted(todo[:size])
    if not chosen:
        raise SystemExit("no trace needs your label right now. Thank you! Watch the issue for the next pool.")
    bid = sha256_bytes(canon([labeller, chosen]))[:10]
    items = []
    for t in chosen:
        for c in pool[t]["checks"]:
            items.append({"trace_id": t, "check_id": c, "rule": rule_text(c), "trace": pool[t], "label": None, "note": ""})
    return {"schema": SCHEMA_BATCH, "batch_id": bid, "labeller": labeller, "created_at": now(),
            "instructions": "Set label to pass, fail or n/a for every item (see docs/contributing/LABELLING.md). Do not run any check, "
                            "do not look at other people's labels, do not use a model. note is optional.",
            "items": items}


def submit(batch_file: Path, base: Path | None = None) -> Path:
    b = json.loads(Path(batch_file).read_text(encoding="utf-8"))
    if b.get("schema") != SCHEMA_BATCH or not HANDLE.match(str(b.get("labeller", ""))):
        raise SystemExit("not a labelling batch file")
    pool, labels = load_pool(base), load_labels(base)
    _, labels_dir, _ = _dirs(base)
    seen = labelled_by(labels)
    out = []
    for it in b["items"]:
        t, c = it.get("trace_id"), it.get("check_id")
        if t not in pool or c not in pool[t]["checks"]:
            raise SystemExit(f"unknown trace or check: {t} {c}")
        if it.get("label") not in VALID:
            raise SystemExit(f"{t} {c}: label must be one of {', '.join(VALID)} (got {it.get('label')!r})")
        if b["labeller"] in seen.get(t, set()):
            raise SystemExit(f"{b['labeller']} already labelled {t}")
        out.append({"trace_id": t, "check_id": c, "label": it["label"], "note": str(it.get("note", ""))[:500]})
    if not out:
        raise SystemExit("the batch has no items")
    pool_dir, _, _ = _dirs(base)
    doc = {"schema": SCHEMA_LABELS, "labeller": b["labeller"], "batch_id": b["batch_id"], "submitted_at": now(),
           "trace_sha256": {x["trace_id"]: sha256_file(pool_dir / f"{x['trace_id']}.json") for x in out}, "labels": out}
    dest = labels_dir / f"{b['labeller']}--{b['batch_id']}.json"
    if dest.exists():
        raise SystemExit(f"{dest.name} already exists")
    labels_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest


# ---------------------------------------------------------------- collect / lock / verify

def collect(base: Path | None = None) -> dict:
    """Per (trace, check): both labels agree -> agreed; differ -> needs a maintainer resolution; <2 labellers -> incomplete."""
    pool, labels = load_pool(base), load_labels(base)
    pool_dir, _, res_dir = _dirs(base)
    by: dict[tuple[str, str], dict[str, str]] = {}
    for f in labels:
        for x in f["labels"]:
            if f["trace_sha256"].get(x["trace_id"]) != sha256_file(pool_dir / f"{x['trace_id']}.json"):
                raise SystemExit(f"{f['_file']}: trace {x['trace_id']} changed after it was labelled")
            by.setdefault((x["trace_id"], x["check_id"]), {})[f["labeller"]] = x["label"]
    final, unresolved, incomplete = [], [], []
    for t, d in pool.items():
        for c in d["checks"]:
            ls = by.get((t, c), {})
            if len(ls) < 2:
                incomplete.append(f"{t} {c}")
                continue
            vals = set(ls.values())
            if len(vals) == 1:
                final.append({"trace_id": t, "check_id": c, "final": vals.pop(), "source": "agreed", "labellers": sorted(ls)})
                continue
            rp = res_dir / f"{t}.{c}.json"
            if rp.exists():
                r = json.loads(rp.read_text(encoding="utf-8"))
                if r.get("final") in VALID and r.get("resolver") and r.get("rationale"):
                    final.append({"trace_id": t, "check_id": c, "final": r["final"], "source": "resolved", "labellers": sorted(ls),
                                  "resolver": r["resolver"]})
                    continue
                raise SystemExit(f"{rp.name}: needs final (pass/fail/n/a), resolver and rationale")
            unresolved.append(f"{t} {c}")
    return {"final": final, "unresolved": unresolved, "incomplete": incomplete}


def _entries(base: Path | None, private: dict | None) -> dict:
    pool_dir, labels_dir, res_dir = _dirs(base)
    res = collect(base)
    if res["unresolved"] or res["incomplete"]:
        raise SystemExit(f"cannot lock: {len(res['unresolved'])} disagreement(s) to resolve, {len(res['incomplete'])} item(s) without two labellers")
    return {"schema": SCHEMA_LOCK,
            "traces": {p.stem: sha256_file(p) for p in sorted(pool_dir.glob("LT-*.json"))},
            "label_files": {p.name: sha256_file(p) for p in sorted(labels_dir.glob("*.json"))},
            "resolution_files": {p.name: sha256_file(p) for p in sorted(res_dir.glob("*.json"))},
            "final_sha256": sha256_bytes(canon(res["final"])), "final_count": len(res["final"]),
            "private_commitments": private or {}}


def lock(base: Path | None = None, out: Path | None = None, private: Path | None = None) -> Path:
    dest = Path(out) if out else (Path(base) if base else LABELLING) / "LOCK.json"
    if dest.exists():
        raise SystemExit(f"{dest} exists: a lock is never overwritten. Start a new round in a new directory.")
    priv = json.loads(Path(private).read_text(encoding="utf-8")) if private else None
    body = _entries(base, priv)
    doc = {**body, "locked_at": now(), "lock_hash": sha256_bytes(canon(body))}
    dest.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    return dest


def verify(base: Path | None = None, lock_file: Path | None = None, predictions: Path | None = None) -> dict:
    """Recompute the hash from the files on disk. Raises SystemExit on any mismatch or a missing lock."""
    lf = Path(lock_file) if lock_file else (Path(base) if base else LABELLING) / "LOCK.json"
    if not lf.exists():
        raise SystemExit(f"no lock manifest at {lf}: labels must be locked before predictions run")
    doc = json.loads(lf.read_text(encoding="utf-8"))
    body = {k: v for k, v in doc.items() if k not in ("lock_hash", "locked_at")}
    fresh = _entries(base, doc.get("private_commitments"))
    if fresh != body:
        raise SystemExit("lock mismatch: a trace, a label file or a resolution changed after the lock")
    if sha256_bytes(canon(body)) != doc["lock_hash"]:
        raise SystemExit("lock hash does not match the manifest body")
    if predictions:
        first = json.loads(Path(predictions).read_text(encoding="utf-8").splitlines()[0])
        if first.get("lock_hash") != doc["lock_hash"]:
            raise SystemExit("predictions do not carry this lock hash on their first line: they were not produced against this lock")
    return doc


def require_lock(base: Path | None = None) -> str:
    """For scoring code: call first. Returns the lock hash, or exits if the labels are not locked and intact."""
    return verify(base)["lock_hash"]


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python scripts/labelling.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("batch", help="write a batch of traces for you to label")
    b.add_argument("--labeller", required=True)
    b.add_argument("--size", type=int, default=10)
    b.add_argument("--out", type=Path)
    s = sub.add_parser("submit", help="validate a filled batch and write your label file")
    s.add_argument("file", type=Path)
    st = sub.add_parser("status", help="counts only")
    co = sub.add_parser("collect", help="maintainer: agreements and disagreements")
    lk = sub.add_parser("lock", help="maintainer: write the lock manifest")
    lk.add_argument("--private-manifest", type=Path, help="JSON of hash commitments for a private split (hashes only)")
    lk.add_argument("--out", type=Path)
    v = sub.add_parser("verify", help="recompute the lock hash")
    v.add_argument("--lock", type=Path)
    v.add_argument("--predictions", type=Path)
    for p in (b, s, lk, v, st, co):
        p.add_argument("--dir", type=Path, help="labelling directory (default: labelling/)")
    a = ap.parse_args(argv)
    base = getattr(a, "dir", None)
    if a.cmd == "batch":
        doc = make_batch(a.labeller, a.size, base)
        out = a.out or Path(f"labelling-batch-{a.labeller}-{doc['batch_id']}.json")
        out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {out}: {len(doc['items'])} item(s). Fill in every label, then: python scripts/labelling.py submit {out}")
    elif a.cmd == "submit":
        dest = submit(a.file, base)
        print(f"wrote {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest}")
        print("Open a pull request with that one file. Do not read other people's label files before you submit yours.")
    elif a.cmd == "status":
        pool, labels = load_pool(base), load_labels(base)
        seen = labelled_by(labels)
        n = [len(seen.get(t, ())) for t in pool]
        print(f"traces: {len(pool)}; with 0 labels: {n.count(0)}; with 1: {n.count(1)}; with 2 or more: {sum(1 for x in n if x >= 2)}")
    elif a.cmd == "collect":
        r = collect(base)
        print(f"agreed or resolved: {len(r['final'])}; disagreements to resolve: {len(r['unresolved'])}; waiting for a second labeller: {len(r['incomplete'])}")
        for u in r["unresolved"]:
            print("  resolve:", u, "(write labelling/resolutions/<trace>.<check>.json with final, resolver, rationale)")
        return 1 if r["unresolved"] else 0
    elif a.cmd == "lock":
        p = lock(base, a.out, a.private_manifest)
        print(f"wrote {p}. Predictions may run only now, and must carry this lock hash.")
    elif a.cmd == "verify":
        d = verify(base, a.lock, a.predictions)
        print(f"lock ok: {d['lock_hash']} ({d['final_count']} labels, locked {d['locked_at']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
