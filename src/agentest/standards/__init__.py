"""Standards-based, agent-agnostic checks (v3.1.0).

Agents are described only by standard, agent-published metadata:

* traces: OpenTelemetry GenAI semantic conventions, exported as OTLP/JSON (``otel.py``);
* agent description: an A2A AgentCard (``agent-card.json``);
* tools: an MCP ``tools/list`` result with ``inputSchema`` (JSON Schema) and
  ``annotations`` (readOnlyHint, destructiveHint, idempotentHint, openWorldHint);
* governance facts the standards do not cover (approval, data classes, limits,
  tenancy, prerequisites) go in ONE documented A2A AgentCard extension,
  ``urn:agentest:a2a-ext:governance:v1`` (non-standard; see docs/standards/EXTENSION.md).

Every one of the 130 checks is one universal rule in ``rules.py``; no agent id
or agent-specific expectation exists anywhere.
"""

from pathlib import Path

VERSION = "3.1.0"
GOV_EXT = "urn:agentest:a2a-ext:governance:v1"
DATA = Path(__file__).parent
