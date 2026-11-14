# Release highlights (v3.x)

Moved from the README. The full history is the [CHANGELOG](../CHANGELOG.md).


> **v3.3.2** (PyPI distribution name `agentest-ai`, import name unchanged; verdicts unchanged). **v3.3.1** (review-fix release: catalogue control_refs regenerated from dataset v1.3.1, full catalogue pinned in CI, single-source version check; verdicts unchanged). **v3.3.0** (seven universal-rule precision fixes from A99–A101 blind test; currency/id/language grounding; 90/90 seeds; 0 one-sided). **v3.2.1** (seed-aware catch-rate 90/90; tight budgets on A90-A97; T6-003 widen; A95/A96/A97 re-seeds). **v3.2.0** (coverage release: A82-A98; 0 one-sided IDs). **v3.1.1** (patch on v3.1.0: stricter guard, OTel `schemaUrl` and retry handling, optional official protobuf
> decoder, real-SDK conformance test, a snapshot of every verdict). **v3.1.0:** every one of the 130 checks is a universal rule over standard artifacts (OpenTelemetry GenAI traces,
> the A2A AgentCard, MCP tool annotations). The legacy v2 engine and its per-agent YAML profiles are removed; the
> `v2.0.0` and `v1.0.0` tags keep that history. See the [CHANGELOG](../CHANGELOG.md) for the migration note.

Give it an agent's OTel GenAI traces (plus, optionally, its A2A AgentCard and MCP tools list) and it returns a
`pass` / `fail` / `n/a` verdict for each of 130 checks: the 110 catalogue IDs plus 20 repo extensions (`X-001`…`X-020`).
No account, token, network or model is needed to judge. The checklist design is informed by ISO 42001 themes; this is
not certification.
