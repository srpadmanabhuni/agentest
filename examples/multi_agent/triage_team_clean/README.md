# triage_team_clean

Supervisor with three workers and a review panel; every run follows its declared delegation graph (control).

Synthetic traces (no model, no network) in OpenTelemetry GenAI conventions plus the documented `agentest.*` extensions. Regenerate with `python scripts/gen_multiagent_examples.py`. See `docs/packs/MULTI-AGENT.md`.

Run the multi-agent checks: `agentest std run --agents examples/multi_agent --agent triage_team_clean --pack ma`

Control agent (5 traces): no MA check may fail on any of them. A check is n/a on a trace that gives it nothing to judge (for example MA-005 when no tool result carries injected content).
