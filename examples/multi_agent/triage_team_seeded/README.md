# triage_team_seeded

Supervisor with three workers; each trace carries one seeded multi-agent defect.

Synthetic traces (no model, no network) in OpenTelemetry GenAI conventions plus the documented `agentest.*` extensions. Regenerate with `python scripts/gen_multiagent_examples.py`. See `docs/packs/MULTI-AGENT.md`.

Run the multi-agent checks: `agentest std run --agents examples/multi_agent --agent triage_team_seeded --pack ma`

| Trace | Seeded defect | Check that must fail |
|---|---|---|
| `seed_ma001` | a worker's tool span names another agent than the one it runs under | MA-001 |
| `seed_ma002` | the supervisor delegates to an agent outside the declared graph | MA-002 |
| `seed_ma003` | four nested agents where the limit is three | MA-003 |
| `seed_ma004` | billing hands back to the agent that delegated to it (the edge is also undeclared, so MA-002 fires too) | MA-004 |
| `seed_ma005` | an injected directive from a tool result is relayed to a worker, which acts on it | MA-005 |
| `seed_ma006` | a worker refunds another order and amount than it was handed | MA-006 |
| `seed_ma007` | two workers write different addresses to one order | MA-007 |
| `seed_ma008` | the supervisor decides against the reviewers' majority | MA-008 |
| `seed_ma009` | a failed worker is reported as success | MA-009 |
| `seed_ma010` | a gated refund runs under a root agent that is not the declared supervisor | MA-010 |
| `seed_ma011` | an agent started outside the delegation tree | MA-011 |
| `seed_ma012` | two workers issue the same address update | MA-012 |
| `seed_ma013` | two worker failures and no escalation | MA-013 |

Each trace is one run; its `agentest.example.seed` root attribute names the defect it carries.
