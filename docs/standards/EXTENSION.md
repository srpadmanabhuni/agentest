# Governance extension `urn:agentest:a2a-ext:governance:v1` (non-standard)

A2A AgentCards allow extensions in `capabilities.extensions[]` (`uri`, `description`, `required`, `params`).
agentest defines one, because no published standard yet carries these governance facts. It is **policy-as-data**
(the same idea as OPA/Rego data documents): plain facts, no expressions, no test IDs, no pass/fail logic.
Every field is optional; a rule whose fact is absent returns `n/a` ("no standard signal").

```json
{"uri": "urn:agentest:a2a-ext:governance:v1", "required": false, "params": {
  "approval": {"required": ["request_refund"], "hostGated": true, "ttlSeconds": 900},
  "dataClassification": {"restricted": ["card", "pan", "acct"]},
  "recipients": {"allow": ["*@shop.example"]},
  "limits": {"max_amount": 50000, "max_tool_calls": 20, "max_steps": 12, "max_tokens": 20000, "max_seconds": 600},
  "tenancy": {"argument": "tenant_id", "sessionTenant": "t-1"},
  "network": {"allowHosts": ["api.shop.example"]},
  "mutuallyExclusive": [["delete_user", "export_csv"]],
  "prerequisites": {"request_refund": ["lookup_order"]},
  "disclosureTools": ["lookup_patient"], "exportTools": ["export_csv"],
  "roles": {"orchestrators": ["Triage agent"], "actors": {"Billing agent": ["lookup_order", "request_refund"]},
            "adminTools": ["disable_branch_protection"], "adminRoles": ["repo-admin"]},
  "compensations": {"reserve_stock": "release_stock"}, "freshness": {"get_fx_rate": 300},
  "breakGlass": {"tools": ["break_glass_access"], "credentialArgs": ["reason"]}, "auditTools": ["write_audit"],
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
| `roles` (`actors`, `orchestrators`) | T3-002, T3-007, T3-009 | A2A has auth schemes, not per-actor tool grants |
| `roles.adminTools`, `roles.adminRoles` (v3.1) | T5-016 | the session's roles come from the OTel `user.roles` attribute; which tools need an admin role is not in MCP |
| `approval.ttlSeconds` (v3.1) | T3-014 | no standard approval lifetime |
| `compensations` (v3.1) | T2-008, T1-008, T1-012 | MCP has no "undo" relation between tools |
| `freshness` (v3.1) | T2-010 | no standard max-age for a tool result |
| `breakGlass` (v3.1) | T3-012 | no standard emergency-access marker; without it a call naming break-glass / emergency access is used |
| `auditTools` (v3.1) | T6-013 | no standard audit marker; without it an `audit` list in `agentest.final_state` is used |
| `capabilities`, `languages` | n/a gating; T7-004, X-014 | partially in AgentCard (`skills[].tags`); kept explicit |
| `slo.successRate` | T1-003 | — |
| `postconditions` | T1-001, T1-002, T1-018 (examples mode only) | success criteria of skill examples; A2A examples are text only |
| `policyCheckTools` | T5-014 | read-only screening tools that must succeed before approval-gated tools; no standard equivalent |

The extension `params` are validated by the JSON Schema [`governance-extension.schema.json`](../../src/agentest/standards/schemas/governance-extension.schema.json) (`agentest std validate`; CI validates every bundled card).

## OTel attributes outside the GenAI conventions (`agentest.*`)

| Attribute / event | Meaning |
|---|---|
| `agentest.input.id`, `agentest.run.rep` | which recorded input and repetition this trace is |
| `agentest.input.families`, `agentest.input.injected`, `agentest.test.canaries`, `agentest.input.relations` | test-side labels of the input (families, injected directive, canaries, metamorphic relations) |
| `user.roles` (**standard** OTel registry attribute) | roles of the session user; read by T5-016 |
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
- Test-input labels (families, the injected directive, canaries) travel in the trace itself as root-span attributes `agentest.input.families`, `agentest.input.injected` and `agentest.test.canaries`. Since v3.1 there is no per-agent `inputs.json`.


## Seeded-defects fixture extension `urn:agentest:a2a-ext:seeded-defects:v1`

Reference agents that are deliberately defective publish this optional AgentCard extension. It is **fixture
metadata**, not governance policy: it lists the catalogue IDs the agent is intentionally seeded to fail so that
coverage / catch-rate reporting counts only those seeds (and does not treat every decided pass on a global target
list as a "miss"). Rules never read this extension; only docs, the viewer and catch-rate tooling do.

```json
{"uri": "urn:agentest:a2a-ext:seeded-defects:v1", "required": false, "params": {
  "catalogueIds": ["T5-006", "X-006", "X-007"]
}}
```

| Field | Used by | Notes |
|---|---|---|
| `catalogueIds` | catch-rate / agent README / viewer status | Catalogue or repo-extension IDs this agent is built to fail. Absent → no seed-aware catch-rate for that agent. |

Governance params stay free of test IDs (see above). Seeds live only in this fixture extension.
