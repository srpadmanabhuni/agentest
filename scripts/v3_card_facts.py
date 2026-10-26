"""Publish success criteria with the AgentCard skill examples, and network facts in the governance extension.

* ``postconditions.byInput`` (keyed by recorded input ids, which an agent cannot know) becomes
  ``postconditions.byExample``: each entry pairs a skill example text (added to ``skills[0].examples`` when
  missing) with the criteria that define success for it.
* ``network.allowHosts`` lists the hosts the agent's own example runs reach (URL arguments of runs that are not
  injection or canary probes); an empty list declares that no external host is expected.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agentest.standards import GOV_EXT, metadata, runner  # noqa: E402
from agentest.standards import inputs as I  # noqa: E402

URL = re.compile(r"https?://([\w.-]+)", re.I)

for aid, a in sorted(metadata.load_all().items()):
    path = a.dir / "agent-card.json" if hasattr(a, "dir") else ROOT / "agents" / aid / "agent-card.json"
    if not path.exists():
        continue
    card = json.loads(path.read_text())
    ext = next(e for e in card["capabilities"]["extensions"] if e["uri"] == GOV_EXT)
    g = ext["params"]
    runs = list(runner.runs(a))
    text = {}
    for r in runs:
        text.setdefault(r.input_id, r.input)
    pc = g.get("postconditions") or {}
    by = pc.pop("byInput", None) or {}
    if by:
        skill = card["skills"][0]
        ex = skill.setdefault("examples", [])
        entries = pc.setdefault("byExample", [])
        for iid, crit in by.items():
            t = text.get(iid)
            if not t or not t.strip():
                continue
            if t not in ex:
                ex.append(t)
            if not any(e["example"] == t for e in entries):
                entries.append({"example": t, "criteria": crit})
        g["postconditions"] = pc
    canary_hosts = {k.lower() for k in I.canaries(a) if "." in k}
    hosts = set()
    for r in runs:
        if I.families(a, r.input_id) & {"injection", "secret"}:
            continue
        for t in r.tools:
            hosts |= {h.lower() for h in URL.findall(json.dumps(t.args))}
    g.setdefault("network", {})["allowHosts"] = sorted(h for h in hosts if not any(h.endswith(c) for c in canary_hosts))
    path.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n")
    print(aid, len(pc.get("byExample", [])), g["network"]["allowHosts"])
