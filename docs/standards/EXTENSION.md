# Governance extension `urn:agentest:a2a-ext:governance:v1` (non-standard)

A2A AgentCards allow extensions in `capabilities.extensions[]` (`uri`, `description`, `required`, `params`).
agentest defines one, because no published standard yet carries these governance facts. It is **policy-as-data**
(the same idea as OPA/Rego data documents): plain facts, no expressions, no test IDs, no pass/fail logic.
Every field is optional; a rule whose fact is absent returns `n/a` ("no standard signal").

```json
{"uri": "urn:agentest:a2a-ext:governance:v1", "required": false, "params": {
  "approval": {"required": ["request_refund"], "hostGated": true},
  "dataClassification": {"restricted": ["card", "pan", "acct"]},
  "recipients": {"allow": ["*@shop.example"]},
  "limits": {"max_amount": 50000, "max_tool_calls": 20, "max_steps": 12, "max_tokens": 20000, "max_seconds": 600},
  "tenancy": {"argument": "tenant_id", "sessionTenant": "t-1"},
  "network": {"allowHosts": ["api.shop.example"]},
  "mutuallyExclusive": [["delete_user", "export_csv"]],
  "prerequisites": {"request_refund": ["lookup_order"]},
  "disclosureTools": ["lookup_patient"], "exportTools": ["export_csv"],
  "roles": {"orchestrators": ["Triage agent"], "actors": {"Billing agent": ["lookup_order", "request_refund"]}},
  "capabilities": {"tools": true, "memory": false, "retrieval": false, "multi_agent": true, "approval": true},
  "languages": ["en", "hi-Latn"],
  "slo": {"successRate": 0.9},
  "postconditions": {"default": [{"path": "output.pending.0.id", "op": "eq", "value": "ORD-1001"}], "byExample": [{"example": "refund order ORD-1001", "criteria": [...]}]}
}}
```

| Field | Used by (examples) | Why no standard covers it |
|---|---|---|
| `approval.required`, `hostGated` | T2-004, T2-012, T3-001..T3-005, X-016, X-017 | MCP has `destructiveHint`, but not "needs human approval" |
| `dataClassification.restricted` | T5-004, X-020, T6-011 | no standard data-class label on tool arguments |
| `recipients.allow` | T4-003, T5-017 | — |
| `limits` | T5-006, X-005, X-006, X-007, amount caps | — |
| `network.allowHosts`, `mutuallyExclusive` | T5-005, T5-017, T4-002, T5-013 | MCP `openWorldHint` says *whether*, not *where* |
| `tenancy`, `exportTools` | T3-008, T5-011 | — |
| `prerequisites`, `disclosureTools` | T2-001, T2-002, T2-005 | — |
| `roles` | T3-002, T5-016 | A2A has auth schemes, not per-actor tool grants |
| `capabilities`, `languages` | n/a gating; T7-004, X-014 | partially in AgentCard (`skills[].tags`); kept explicit |
| `slo.successRate` | T1-003 | — |
| `postconditions` | T1-001, T1-002, T1-018 (examples mode only) | success criteria of skill examples; A2A examples are text only |
| `policyCheckTools` | T5-014 | read-only screening tools that must succeed before approval-gated tools; no standard equivalent |

The extension `params` are validated by the JSON Schema [`governance-extension.schema.json`](../../src/agentest/standards/schemas/governance-extension.schema.json) (`agentest std validate`; CI validates every bundled card).

## OTel attributes outside the GenAI conventions (`agentest.*`)

| Attribute / event | Meaning |
|---|---|
| `agentest.input.id`, `agentest.run.rep` | which recorded input and repetition this trace is |
| `agentest.tool.reason` | the agent's stated reason for a tool call (T5-015, X-003) |
| `agentest.source.seq`, `agentest.source.time_s` | original log order / timestamps (T2-014) |
| `agentest.citations` | memory/source items the agent says it used (T6-007, T6-009) |
| `agentest.outputs`, `agentest.final_state` | structured outputs and the observed end state (typed JSON: `$set`, `$frozenset`, `$bytes`) |
| span `agentest.approval` + events `agentest.approval.decision` | approval requests and decisions (actor, action, object, version) |
| event `agentest.state_change` | durable effects reported by the system of record |
| event `gen_ai.evaluation.result` | **standard** (semconv GenAI, status Development): harness verdicts |

Proposal: upstream `agentest.tool.reason` and the approval span to the OTel GenAI SIG, and approval/data-class
facts to MCP annotations; when they exist, the extension field becomes an alias.

### Notes on `postconditions` and `network`
- `postconditions.byExample` ties success criteria to the AgentCard `skills[].examples` text. Lookup goes by normalised input text, then by the legacy `byInput`, then by `default`. `scripts/v3_card_facts.py` migrates the older format.
- `network.allowHosts: []` means the agent may contact no hosts. If the key is absent, egress is undeclared.
- `inputs.json` `inputs[id].injected` records the directive that a test input injects. It is used to derive canaries (`scripts/v3_injected.py`).
