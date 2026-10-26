"""Agent profile: everything agent-specific, declared once in YAML.

Schema (all keys optional unless noted)::

  agent: a05                     # required
  framework: OpenAI Agents SDK
  adapter: openai_agents         # required: dialect in agentest.model.adapters
  tools: {lookup_order: read, request_refund: write}
  approval_required: [request_refund]
  allowed_recipients: ["@acme.example"]       # suffixes allowed in to/recipient args
  limits: {max_amount: 50000}
  sensitive: [email, card, pan, acct]          # PII kinds that must not reach tool args
  canaries: [CANARY-7Q, evil.example]
  languages: [en, hi-Latn]
  capabilities: {tools: true, memory: false, retrieval: false, multi_agent: true, approval: true}
  orchestrators: [Triage agent]                # actors that must hold no privileged tool
  observations:                                # where the agent exposes facts in its recorded output
    final_answer: [output.final_answer]
    executed: [extra.refunded_before_human]    # effects that really happened (before any human step)
    pending: [output.pending_refunds]
    approvals: [output.approval_audit]
    citations: [output.sources]
  probes:                                      # probe roles (names of recorded probes)
    canonical: [canon]
    empty: [empty]
    readonly: [faq]
    injection: [inject]
    social: [social]                           # approval text inside the request
    metamorphic: [[canon, hinglish]]           # pairs that must give the same outcome
  success:                                     # declarative success criteria (all must hold)
    - {path: output.pending_refunds, op: nonempty}
  metamorphic_key: output.pending_refunds      # value compared across metamorphic pairs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentest.paths import root


def get_path(d: Any, path: str) -> Any:
    """Dotted lookup (``output.a.b``; integer parts index lists); missing -> None."""
    cur = d
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.lstrip("-").isdigit():
            i = int(part)
            cur = cur[i] if -len(cur) <= i < len(cur) else None
        else:
            return None
    return cur


@dataclass
class Profile:
    agent: str
    adapter: str
    framework: str = ""
    tools: dict[str, str] = field(default_factory=dict)
    approval_required: list[str] = field(default_factory=list)
    allowed_recipients: list[str] = field(default_factory=list)
    limits: dict[str, float] = field(default_factory=dict)
    sensitive: list[str] = field(default_factory=list)
    canaries: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=lambda: ["en"])
    capabilities: dict[str, bool] = field(default_factory=dict)
    orchestrators: list[str] = field(default_factory=list)
    observations: dict[str, list[str]] = field(default_factory=dict)
    probes: dict[str, list] = field(default_factory=dict)
    success: list[dict] = field(default_factory=list)
    metamorphic_key: str = ""
    notes: str = ""
    episodes: str = ""  # optional glob of native episode .jsonl files, relative to the profile file
    source: str = ""  # set by load(): the profile file path

    def side_effect(self, tool: str) -> str:
        return self.tools.get(tool, "unknown")

    def cap(self, name: str) -> bool:
        return bool(self.capabilities.get(name, False))

    def role(self, r: str) -> list:
        return list(self.probes.get(r, []) or [])


def _yaml():
    try:
        import yaml
    except ImportError as e:  # pragma: no cover
        raise SystemExit("agent profiles need PyYAML: pip install 'agentest[model]'") from e
    return yaml


def load(path: Path | str) -> Profile:
    d = _yaml().safe_load(Path(path).read_text())
    known = set(Profile.__dataclass_fields__) - {"source"}
    unknown = set(d) - known
    if unknown:
        raise ValueError(f"{path}: unknown profile keys {sorted(unknown)}")
    return Profile(**d, source=str(Path(path).resolve()))


def profiles_dir() -> Path:
    return root() / "profiles"


def load_all(d: Path | None = None) -> dict[str, Profile]:
    d = d or profiles_dir()
    return {p.agent: p for p in (load(f) for f in sorted(d.glob("*.yaml")))}
