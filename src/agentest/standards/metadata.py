"""Load an agent's standard, agent-published metadata.

Per agent directory (``agents/<id>/``)::

  agent-card.json   A2A AgentCard (https://a2a-protocol.org/latest/specification/#5-agent-discovery-the-agent-card)
                    incl. the governance extension in capabilities.extensions[] (urn:agentest:a2a-ext:governance:v1)
  tools.json        MCP tools/list result: name, description, inputSchema (JSON Schema 2020-12),
                    annotations {readOnlyHint, destructiveHint, idempotentHint, openWorldHint}
                    (https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
  adapter.json      how to MAP the framework's native logs to OTel GenAI spans (dialect + field paths).
                    No pass/fail logic is allowed here.
  inputs.json       the recorded test inputs: input id -> generated input family (see inputs.py).

None of these files may contain test expectations, rules or catalogue IDs
(enforced by tests/test_standards_guard.py).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from agentest.paths import root
from agentest.standards import GOV_EXT

ANNOTATION_DEFAULTS = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": True}  # MCP defaults
CARD_REQUIRED = ("protocolVersion", "name", "description", "url", "version", "capabilities", "defaultInputModes", "defaultOutputModes", "skills")
SKILL_REQUIRED = ("id", "name", "description", "tags")


@dataclass
class Agent:
    id: str
    dir: Path
    card: dict
    tools: dict[str, dict]
    adapter: dict
    inputs: dict
    gov: dict = field(default_factory=dict)

    def ann(self, tool: str, key: str) -> bool:
        t = self.tools.get(tool)
        if t is None:
            return ANNOTATION_DEFAULTS[key]
        return bool(t.get("annotations", {}).get(key, ANNOTATION_DEFAULTS[key]))

    def is_write(self, tool: str) -> bool:
        """A call that may change state: MCP readOnlyHint false (unknown tools are treated as writes, the MCP default)."""
        return not self.ann(tool, "readOnlyHint")

    def is_destructive(self, tool: str) -> bool:
        return self.is_write(tool) and self.ann(tool, "destructiveHint")

    def g(self, *path, default=None):
        cur = self.gov
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return default
            cur = cur[p]
        return cur

    def cap(self, name: str) -> bool:
        return bool(self.g("capabilities", name, default=False))

    def schema(self, tool: str) -> dict:
        return (self.tools.get(tool) or {}).get("inputSchema") or {}


def agents_dir() -> Path:
    return root() / "agents"


def validate(a: Agent) -> list[str]:
    """Structural checks of the AgentCard and MCP tool descriptors (subset of the published schemas)."""
    errs = [f"agent-card: missing {k}" for k in CARD_REQUIRED if k not in a.card]
    for s in a.card.get("skills", []):
        errs += [f"skill {s.get('id')}: missing {k}" for k in SKILL_REQUIRED if k not in s]
    for ext in a.card.get("capabilities", {}).get("extensions", []):
        if "uri" not in ext:
            errs.append("extension without uri")
    for name, t in a.tools.items():
        if t.get("inputSchema", {}).get("type") != "object":
            errs.append(f"tool {name}: inputSchema.type must be 'object'")
        bad = set(t.get("annotations", {})) - {"title", *ANNOTATION_DEFAULTS}
        if bad:
            errs.append(f"tool {name}: unknown annotations {sorted(bad)}")
    return errs


OTLP_ONLY = {"dialect": "otlp", "files": ["*.otlp.json", "*.otlp.jsonl", "traces/*.json", "traces/*.jsonl"]}


def _is_agent_dir(x: Path) -> bool:
    return (x / "agent-card.json").exists() or any(x.glob("*.otlp.json*")) or (x / "traces").is_dir()


def load(d: Path) -> Agent:
    """Load an agent directory. Only OTLP traces are required: a missing AgentCard, tools.json or adapter.json
    degrades the rules that need them to n/a (no governance facts, MCP defaults for undeclared tools)."""
    card = json.loads((d / "agent-card.json").read_text()) if (d / "agent-card.json").exists() else {"name": d.name, "skills": []}
    tl = json.loads((d / "tools.json").read_text()) if (d / "tools.json").exists() else {"tools": []}
    ad = json.loads((d / "adapter.json").read_text()) if (d / "adapter.json").exists() else dict(OTLP_ONLY)
    inp = json.loads((d / "inputs.json").read_text()) if (d / "inputs.json").exists() else {}
    gov = next((e.get("params", {}) for e in card.get("capabilities", {}).get("extensions", []) if e.get("uri") == GOV_EXT), {})
    return Agent(d.name, d, card, {t["name"]: t for t in tl.get("tools", [])}, ad, inp, gov)


def load_all(d: Path | None = None) -> dict[str, Agent]:
    d = d or agents_dir()
    return {x.name: load(x) for x in sorted(d.iterdir()) if x.is_dir() and _is_agent_dir(x)}
