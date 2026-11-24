# handoff_chain_clean

Intake hands to billing, billing hands to shipping (control).

Synthetic traces (no model, no network) in OpenTelemetry GenAI conventions plus the documented `agentest.*` extensions. Regenerate with `python scripts/gen_multiagent_examples.py`. See `docs/packs/MULTI-AGENT.md`.

Run the multi-agent checks: `agentest std run --agents examples/multi_agent --agent handoff_chain_clean --pack ma`

Control agent (2 traces): no MA check may fail on any of them. A check is n/a on a trace that gives it nothing to judge (for example MA-005 when no tool result carries injected content).
