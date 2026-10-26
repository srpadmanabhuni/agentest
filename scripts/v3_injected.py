"""Record the injected payload of each injection input in agents/<id>/inputs.json (test-owned stimulus data).

The payload comes from the harness case annotation (``extra.case``), where the injected directive is quoted.
Only inputs whose own text carries no directive are annotated (they were delivered through tool
results or attachments that the trace does not carry)."""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agentest.standards.rules import DIRECTIVE_WORD, directives  # noqa: E402

for ad in sorted((ROOT / "agents").iterdir()):
    eps = sorted(glob.glob(str(ROOT / "fixtures/real/episodes" / f"{ad.name}.jsonl"))) + sorted(glob.glob(str(ROOT / "fixtures/real/episodes" / f"{ad.name}.b*.jsonl")))
    if not eps or not (ad / "inputs.json").exists():
        continue
    inp = json.loads((ad / "inputs.json").read_text())
    changed = False
    for f in eps:
        for line in open(f):
            d = json.loads(line)
            case = str((d.get("extra") or {}).get("case") or "")
            text = json.dumps(d.get("input"), ensure_ascii=False) if not isinstance(d.get("input"), str) else d["input"]
            if directives(text):
                continue  # the input itself carries the directive (possibly paraphrased in the annotation)
            for q in re.findall(r"'([^']{8,})'", case):
                if re.search(r"(?i)\b(ai|agent|assistant|evaluator|moderator|bot)\b", q) and DIRECTIVE_WORD.search(q) and q.lower() not in text.lower():
                    ent = inp.setdefault("inputs", {}).setdefault(d["probe"], {})
                    fams = ent.setdefault("families", [])
                    if "injection" not in fams:
                        fams.append("injection")
                    if q not in ent.setdefault("injected", []):
                        ent["injected"].append(q)
                        changed = True
    if changed:
        (ad / "inputs.json").write_text(json.dumps(inp, indent=2, ensure_ascii=False) + "\n")
        print(ad.name, {k: v["injected"] for k, v in inp["inputs"].items() if v.get("injected")})
