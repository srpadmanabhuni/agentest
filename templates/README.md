# Starter templates

Minimal files that unlock the most checks. Copy `my_agent/` next to your agent, rename it, and replace the example values with your own.

| file | what it unlocks |
|---|---|
| `my_agent/agent-card.json` | A2A AgentCard plus the agentest governance extension: approval, prerequisites, data classes, recipients, network, languages and limits (docs/standards/EXTENSION.md) |
| `my_agent/tools.json` | MCP `tools/list` with `inputSchema` and the annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) |
| `native-records.json` + `import-map.json` | a chat-message log for two inputs (a canonical one and an empty one). Each call carries a `reason` and the approval decision is recorded with `policy_version`. Regenerate the trace with `agentest std import templates/native-records.json --map templates/import-map.json --tools templates/my_agent/tools.json --service my_agent --out templates/my_agent/traces/my_agent.otlp.jsonl` |

`agentest std run --agents templates` passes 39 checks and fails none. Run `agentest std lint <traces> --card ... --tools ...` to list the fields that are still missing and the checks each one would unlock. `python scripts/template_uplift.py` measures how far each template cuts the n/a share on the demo agents.
