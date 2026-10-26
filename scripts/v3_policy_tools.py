"""One-time metadata migration: publish ``policyCheckTools`` in the governance extension.

T5-014 used to infer policy-check tools from tool-name words (policy/check/screen/verify). The rule now reads the
declared list, so it no longer depends on tool names. This script writes the list once, for the read-only tools
that the old name heuristic would have picked.
"""

import json
import re
import sys
from pathlib import Path

GOV_EXT = "urn:agentest:a2a-ext:governance:v1"
roots = [Path(p) for p in (sys.argv[1:] or ["agents", "examples/agnostic_demo/agents", "examples/model_driven/agents"])]
for root in roots:
    for d in sorted(p for p in root.iterdir() if (p / "agent-card.json").exists()):
        card = json.loads((d / "agent-card.json").read_text())
        tools = json.loads((d / "tools.json").read_text()) if (d / "tools.json").exists() else {}
        tools = tools.get("tools", tools) if isinstance(tools, dict) else tools
        chk = sorted(t["name"] for t in tools if re.search(r"policy|check|screen|verify", t["name"], re.I)
                     and (t.get("annotations") or {}).get("readOnlyHint"))
        ext = next((e for e in card.get("capabilities", {}).get("extensions", []) if e.get("uri") == GOV_EXT), None)
        if ext is None or not chk:
            continue
        ext.setdefault("params", {})["policyCheckTools"] = chk
        (d / "agent-card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n")
        print(d.name, chk)
