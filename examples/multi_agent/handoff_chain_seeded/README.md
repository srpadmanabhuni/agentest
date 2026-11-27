# handoff_chain_seeded

Intake -> billing -> shipping chain; each trace carries one seeded handoff defect.

Synthetic traces (no model, no network) in OpenTelemetry GenAI conventions plus the documented `agentest.*` extensions. Regenerate with `python scripts/gen_multiagent_examples.py`. See `docs/packs/MULTI-AGENT.md`.

Run the multi-agent checks: `agentest std run --agents examples/multi_agent --agent handoff_chain_seeded --pack ma`

| Trace | Seeded defect | Check that must fail |
|---|---|---|
| `seed_chain_loop` | intake and billing bounce the case back and forth three times (the back edge is undeclared, so MA-002 fires too) | MA-004 |
| `seed_chain_context` | billing refunds another order and amount than it was handed | MA-006 |
| `seed_chain_failure` | a failed shipping step is reported as done | MA-009 |
| `seed_chain_edge` | intake hands straight to shipping, skipping billing | MA-002 |

Each trace is one run; its `agentest.example.seed` root attribute names the defect it carries.
