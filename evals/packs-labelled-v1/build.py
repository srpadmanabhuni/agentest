"""Build the locked labelled set: data/*.jsonl.gz (scenarios), labels.jsonl, tools_std.json, MANIFEST.json.

Run:  python build.py          (deterministic: same sources -> byte-identical files)
Nothing here imports or calls a check (``evaluate``, a rule or a pack module); labels are the ones written in author/*.py
and, for the example traces, the seeded-defect tables of examples/multi_agent/*/README.md.
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / "author"))
sys.path.insert(0, str(ROOT / "src"))

import importlib  # noqa: E402

import kit  # noqa: E402

for _m in ("ma", "pv", "rt", "bf", "ex", "dl", "rai"):  # importing a module registers its scenarios
    importlib.import_module(_m)

MA_IDS = [f"MA-{i:03d}" for i in range(1, 14)]


def wjson_gz(path: Path, rows: list[dict]) -> None:
    raw = "".join(kit.dumps(r) + "\n" for r in rows).encode("utf-8")
    with open(path, "wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(raw)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def example_scenarios() -> tuple[list[dict], list[dict]]:
    scen, labels = [], []
    base = ROOT / "examples" / "multi_agent"
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        card = json.loads((d / "agent-card.json").read_text())
        gov = next(e["params"] for e in card["capabilities"]["extensions"] if "governance" in e["uri"])
        tools = {t["name"]: t for t in json.loads((d / "tools.json").read_text())["tools"]}
        readme = (d / "README.md").read_text()
        table = {}
        for m in re.finditer(r"^\|\s*`(?P<trace>[^`]+)`\s*\|(?P<defect>[^|]*)\|\s*(?P<must>MA-\d{3})\s*\|", readme, re.M):
            extra = re.findall(r"(MA-\d{3}) fires too", m.group("defect"))
            table[m.group("trace")] = [m.group("must"), *extra]
        clean = "control" in readme.lower() and not table
        lines = (d / "traces" / f"{d.name}.otlp.jsonl").read_text().splitlines()
        for k, line in enumerate(x for x in lines if x.strip()):
            doc = json.loads(line)
            root = next(s for s in doc["resourceSpans"][0]["scopeSpans"][0]["spans"] if not s.get("parentSpanId"))
            attrs = {a["key"]: next(iter(a["value"].values())) for a in root["attributes"]}
            seed = attrs.get("agentest.input.id") if attrs.get("agentest.example.seed") else None
            sid = f"EX.{d.name}.{k:02d}" + (f".{seed}" if seed else "")
            if clean:
                want = {c: "clean" for c in MA_IDS}
                why = f"{d.name}/README.md: control agent, 'no MA check may fail on any of them'"
            elif seed in table:
                want = {c: "defect" for c in table[seed]}
                why = f"{d.name}/README.md seeded-defect table: {seed} -> {', '.join(table[seed])} must fail"
            else:
                continue
            scen.append({"scenario_id": sid, "source": "example_trace", "check_ids": sorted(want), "gov": gov, "tools_full": tools, "traces": [doc]})
            for c, lab in sorted(want.items()):
                labels.append({"scenario_id": sid, "check_id": c, "label": lab, "expected_status": "fail" if lab == "defect" else "not-fail", "kind": "example_seeded" if lab == "defect" else "example_clean",
                               "pattern": seed or "control", "variant": k, "spec_clause": kit.SPEC[c], "provenance": why})
    return scen, labels


def main() -> None:
    data = HERE / "data"
    data.mkdir(exist_ok=True)
    for f in data.glob("*.jsonl.gz"):
        f.unlink()
    by: dict[str, list[dict]] = defaultdict(list)
    labels: list[dict] = []
    for r in kit.REG:
        s = dict(r["scenario"])
        s["source"] = "synthetic_authored"
        s["check_ids"] = [s["check_id"]]
        by[s["check_id"]].append(s)
        labels.append(r["label"])
    exs, exl = example_scenarios()
    by["EXAMPLES-MA"] = exs
    labels += exl
    ids = [s["scenario_id"] for v in by.values() for s in v]
    assert len(ids) == len(set(ids)), "duplicate scenario ids"
    for name, rows in sorted(by.items()):
        wjson_gz(data / f"{name}.jsonl.gz", sorted(rows, key=lambda x: x["scenario_id"]))
    labels.sort(key=lambda x: (x["check_id"], x["scenario_id"]))
    (HERE / "labels.jsonl").write_text("".join(kit.dumps(x) + "\n" for x in labels), encoding="utf-8")
    (HERE / "tools_std.json").write_text(kit.dumps(kit.TOOLS_STD) + "\n", encoding="utf-8")
    counts: dict[str, dict[str, int]] = {}
    for x in labels:
        counts.setdefault(x["check_id"], Counter())[x["label"]] += 1
    for c, k in counts.items():
        assert k["defect"] >= 15 and k["clean"] >= 15, (c, dict(k))
    files = sorted([*data.glob("*.jsonl.gz"), HERE / "labels.jsonl", HERE / "tools_std.json"])
    code = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    man = {
        "dataset": "packs-labelled-v1", "locked_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).isoformat(timespec="seconds"),
        "checks_code_commit": code, "authors": kit.AUTHOR,
        "statement": "Labels were written in author/*.py (and the example READMEs) before any of the 46 checks was run on any scenario of this set. No prediction exists at lock time. The checks must not be tuned against this set; a fix needs a fresh held-out set to re-measure.",
        "caveats": ["labels are self-authored by the author who also wrote the checks (independence is partial)", "traces are synthetic (Synth) except nothing: no real agent traces", "example-trace labels come from READMEs written together with the checks", "not an independent held-out measurement"],
        "n_scenarios": len(ids), "n_labels": len(labels),
        "per_check": {c: dict(k) for c, k in sorted(counts.items())},
        "files": {f.relative_to(HERE).as_posix(): sha(f) for f in files},
    }
    man["lock_hash"] = hashlib.sha256(json.dumps(man["files"], sort_keys=True).encode()).hexdigest()
    (HERE / "MANIFEST.json").write_text(json.dumps(man, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("n_scenarios", "n_labels", "lock_hash", "locked_at")}, indent=1))
    print("rules imported by authoring:", "agentest.standards.rules" in sys.modules)


if __name__ == "__main__":
    main()
