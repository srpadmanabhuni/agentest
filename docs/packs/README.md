# Extension packs (opt-in, outside the 130)

The 110 catalogue tests and the 130 default checks are fixed: `agentest std run` still reports exactly 130 IDs. Extension packs add checks with their own ID prefixes for areas the core set covers thinly. They are never part of the default run; select them with `--pack` or `--ids`.

| Pack | Prefix | Checks | Covers | Page |
|---|---|---:|---|---|
| `ma` | MA | 13 | Multi-agent | [MULTI-AGENT.md](MULTI-AGENT.md) |
| `pv` | PV | 8 | Privacy | [PRIVACY.md](PRIVACY.md) |
| `rt` | RT | 6 | Red-teaming | [RED-TEAMING.md](RED-TEAMING.md) |
| `bf` | BF | 5 | Bias and fairness | [BIAS-FAIRNESS.md](BIAS-FAIRNESS.md) |
| `ex` | EX | 5 | Explainability | [EXPLAINABILITY.md](EXPLAINABILITY.md) |
| `dl` | DL | 4 | Data-lineage | [DATA-LINEAGE.md](DATA-LINEAGE.md) |
| `rai` | T1-, T3-, T7- | 5 | the five responsible-AI additions (T1-020, T1-021, T3-018, T3-019, T7-017) | [catalog/rai-additions-v1.4.0.jsonl](../../catalog/rai-additions-v1.4.0.jsonl) |

Total: 41 pack checks plus the 5 `rai` additions.

## Run them

```bash
agentest list --packs                      # every pack name and its size
agentest list --pack ma                    # the checks in one pack
agentest std run --agent a01 --pack ma,pv  # run packs on a bundled agent (comma-separated)
agentest std run --agent a01 --ids MA-001,T3-018
agentest std run --agents examples/multi_agent --agent triage_team_seeded --pack ma
```

`--pack` and `--ids` accept pack IDs, the five `rai` additions and the 130 default IDs in any mix. `--pack all` is the default 130.

## How the packs work

- **Offline and deterministic.** Rules read recorded OTLP/JSON traces (OpenTelemetry GenAI conventions) and the agent's published metadata (A2A AgentCard, MCP tools, the governance extension). No model, no network, no per-agent adapter.
- **Agent- and framework-agnostic.** No rule names an agent or a framework.
- **Cannot verify is not fail.** When the attributes or the spec a check needs are absent the verdict is n/a, with the missing observable in the detail.
- **Governance facts** for the packs are optional AgentCard extension fields (`multiAgent`, `privacy`, `fairness` thresholds), documented in [docs/standards/EXTENSION.md](../standards/EXTENSION.md) and validated by the bundled JSON Schema.
- **Catalogue files.** `catalog/packs/<pack>.jsonl` has one row per check (id, title, rule, family, oracle, requires, na_when, severity, references); `catalog/packs/references.json` holds the cited sources. Sources are limited to resolvable references (arXiv, OWASP, specification pages, DOIs); none is invented.
- **Examples.** `examples/multi_agent/` has clean control agents and seeded-defect agents; `agentest.standards.packs.synth` builds small synthetic traces for your own tests.

## Why packs and not more core tests

Opt-in packs keep the published 110 / 130 numbers and their measured behaviour stable while new areas mature. A pack check can graduate into the core set later by an explicit catalogue change; until then it never changes a default verdict.
