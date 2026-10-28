# RFC 0001: A2A governance extension `urn:agentest:a2a-ext:governance:v1`

| | |
|---|---|
| **Status** | Open: draft for comment, not a standard, no stability promise beyond `v1` below |
| **Extension URI** | `urn:agentest:a2a-ext:governance:v1` |
| **Schema** | [`governance-extension.schema.json`](../../src/agentest/standards/schemas/governance-extension.schema.json) (JSON Schema 2020-12) |
| **Reference consumer** | agentest `std` rule engine (`src/agentest/standards/rules.py`) |
| **Reference producers** | `agentest std governance --from mcp|langgraph|autogen|crewai` (`src/agentest/standards/governance.py`) |
| **Author / contact** | Dr Srinivas Padmanabhuni, srinivas AT testAIng.com |
| **Comments** | open an issue or pull request on the agentest repository |

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are to be read as described in RFC 2119 and RFC 8174
when, and only when, they appear in capitals.

## 1. Abstract

An A2A AgentCard says what an agent can do. It does not say which of the agent's tools need a human approval,
which data must never leave it, how often it may call a tool, or which tool undoes another. This document
defines an optional AgentCard extension that publishes those **governance facts as plain data**, so that any
tester, gateway or auditor can check observed behaviour (OpenTelemetry GenAI traces) against what the agent
itself declares. The extension contains no expressions, no test identifiers and no pass/fail logic.

## 2. Motivation and non-goals

* **Motivation.** Without published facts, a checker either guesses (false failures) or writes per-agent
  configuration (lock-in, drift). With them, the same generic checks run on every agent and a missing fact
  yields an explicit "not applicable", never a guessed failure.
* **Non-goals.** This is not a policy language (use OPA/Rego, Cedar, ... for that), not an authorisation
  protocol (A2A security schemes cover authentication), and not a runtime enforcement mechanism. It does not
  replace MCP tool annotations; where an MCP annotation exists, it is used (section 7).

## 3. Declaration

The extension is declared in the AgentCard's `capabilities.extensions[]` array:

```json
{"capabilities": {"extensions": [
  {"uri": "urn:agentest:a2a-ext:governance:v1", "required": false,
   "description": "governance facts (policy as data)",
   "params": {"approval": {"required": ["request_refund"]}, "limits": {"max_tool_calls": 20}}}
]}}
```

* `uri` MUST be exactly `urn:agentest:a2a-ext:governance:v1`.
* `required` SHOULD be `false`: clients that do not understand the extension can still talk to the agent.
* `params` MUST validate against the schema. An AgentCard MUST NOT carry more than one entry with this URI.

## 4. Processing model

1. **Every field is optional.** A consumer MUST treat an absent field as "not declared". A check that needs an
   undeclared fact MUST report *not applicable* (agentest: `n/a`, reason "no standard signal") rather than
   pass or fail.
2. **Tool names** are MCP `tools/list` names of the agent's own tools. A name that the agent does not expose
   is not an error; it simply never matches.
3. **Agent names** (in `roles`) are the `gen_ai.agent.name` values the agent emits in its OTel spans.
4. **Unknown fields** are a schema error in `v1` (`additionalProperties: false`). Producers that need private
   facts SHOULD use a separate extension URI. Consumers MAY ignore unknown fields in later minor revisions.
5. **Precedence.** Published `params` win over every derived source. A consumer MAY derive missing facts from
   MCP tool annotations (section 7) or framework configuration (section 8) and MUST mark them as derived.
6. **Self-assertion.** The facts are the agent owner's claims. A consumer checks behaviour *against* them; it
   MUST NOT treat them as proof that the behaviour is safe (section 10).

## 5. Fields

Types refer to JSON. "tools" means an array of unique tool-name strings.

### 5.1 Human oversight

| Field | Type | Meaning |
|---|---|---|
| `approval.required` | tools | Each call to one of these tools MUST be preceded, in the same run, by a granted approval (OTel span `agentest.approval`, decision `allow`) naming the same action. |
| `approval.hostGated` | boolean | The host, not the agent, blocks unapproved effects. Checks then judge observed effects (`agentest.state_change`), not attempted calls. |
| `approval.ttlSeconds` | number > 0 | A granted approval is valid for this long. |
| `breakGlass.tools` | tools | Emergency-access tools. A call needs a prior named approval and a justification. |
| `breakGlass.credentialArgs` | string[] | Arguments that carry the justification (default `justification`, `reason`, `ticket`, `incident`). |
| `policyCheckTools` | tools | Read-only screening tools that MUST succeed before any approval-gated tool runs. |
| `auditTools` | tools | Tools that write an audit entry. Each turn that changes state SHOULD call one. |

### 5.2 Order and consistency

| Field | Type | Meaning |
|---|---|---|
| `prerequisites` | object: tool → tools | The listed tools MUST have succeeded before the key tool runs. |
| `mutuallyExclusive` | tools[] | No run uses every tool of one set. |
| `compensations` | object: tool → tool | The value tool undoes the key tool. After a failed write, earlier compensable writes SHOULD be undone newest first. |
| `freshness` | object: tool → seconds ≥ 0 | Maximum age of that read tool's result when a later call depends on it. |
| `postconditions.default` / `.byExample[]` / `.byInput` | criteria | Success criteria on the structured end state (`path`, `op` in `eq ne nonempty truthy empty falsy contains excludes le ge`, `value`). `byExample` ties criteria to AgentCard `skills[].examples` text; `byInput` is the legacy form. |

### 5.3 Data and egress

| Field | Type | Meaning |
|---|---|---|
| `dataClassification.restricted` | string[] | Data kinds that MUST NOT appear raw in outputs or tool arguments. Kinds with a defined detector: `card`, `pan`, `acct`, `ssn`, `email`, `phone`; other kinds are accepted and MAY be ignored. |
| `disclosureTools` | tools | Tools that reveal personal data. |
| `exportTools` | tools | Bulk export tools. |
| `recipients.allow` | string[] | Allowed recipient addresses. An address is allowed when it ends with an entry (case-insensitive), e.g. `@shop.example`. When absent, the objects named in the request or returned by earlier tools are the fence. |
| `network.allowHosts` | string[] | Allowed outbound hosts. An empty array means none; an absent key means egress is undeclared. |
| `tenancy` | object | `sessionTenant` and `argument` (the tool argument carrying the tenant, default `tenant_id`). A successful write (or export) whose tenant argument differs from the session tenant is a violation. |

### 5.4 Roles

| Field | Type | Meaning |
|---|---|---|
| `roles.orchestrators` | string[] | Agents that route work: once a handoff has started they MUST NOT make state-changing calls themselves. |
| `roles.actors` | object: agent → tools | The tools each agent may call. |
| `roles.adminTools` / `roles.adminRoles` | tools / string[] | Tools that need one of these roles in the session's OTel `user.roles` attribute. |

### 5.5 Budgets and service levels

| Field | Type | Meaning |
|---|---|---|
| `limits.max_steps`, `max_tool_calls`, `max_tokens`, `max_seconds`, `max_amount` | number | Per-run caps. Other numeric keys are allowed for amount-like caps. |
| `limits.max_span_seconds` | number, or object: span operation → number | p95 duration limit per call (`execute_tool`, `chat`, ...). |
| `rateLimits` | object: tool → `{minIntervalMs, maxCalls, perSeconds}` | Published per-tool rate limits checked against span start times. |
| `slo.successRate` | number in [0, 1] | Target task-success rate over repeated runs. |

### 5.6 Capabilities, language, fairness

| Field | Type | Meaning |
|---|---|---|
| `capabilities` | object: name → boolean | `tools`, `memory`, `retrieval`, `multi_agent`, `approval` (others allowed). `false` makes the matching checks not applicable. |
| `languages` | string[] (BCP 47) | Languages the agent replies in; consumers MAY map primary subtags to Unicode scripts. |
| `fairness.attributes[]` | `{name, values}` | Protected attributes; each value is a token or a list of coupled tokens (e.g. name + pronoun). |
| `fairness.favorable` | `{tools}` or `{field, values}` | What counts as the favourable outcome. |
| `fairness.maxFlipRate`, `maxLengthRatio` | number | Allowed outcome flip rate (default 0) and reply-length ratio (default 2) across counterfactual variants. |

The full example and the mapping of each field to agentest checks are in
[`docs/standards/EXTENSION.md`](../standards/EXTENSION.md).

## 6. Conformance

* A **producer** conforms when the `params` it publishes validate against the schema and every tool and agent
  name refers to the agent's own MCP tools and OTel agent names.
* A **consumer** conforms when it (a) reports *not applicable* for checks whose facts are undeclared,
  (b) never lets derived facts override published ones, and (c) reports which facts were derived.

## 7. MCP tool-annotation hint fallback

When an agent publishes no governance extension, a consumer MAY derive a subset from MCP `tools/list`:

| MCP | Derived field |
|---|---|
| `annotations.readOnlyHint = false` and `destructiveHint = true` (MCP defaults: `false`, `true`) | `approval.required` |
| `annotations.rateLimit` or `_meta.rateLimit` (same shape as `rateLimits` values) | `rateLimits` |
| a non-empty tool list | `capabilities.tools = true` |

MCP annotations are hints, untrusted unless the server is trusted, so derived facts are weaker than published
ones. agentest applies this fallback only when asked (`governance_fallback: mcp` in the config, or
`AGENTEST_GOVERNANCE_FALLBACK=mcp`); its approval checks already fall back to destructive MCP tools natively.

## 8. Framework mappings (informative)

`agentest std governance --from <framework> config.json [--tools tools.json] [--card agent-card.json]` derives
params from framework configuration without importing the framework (plain dicts or duck-typed objects):

| Framework | Fact | Derived field |
|---|---|---|
| LangGraph | `interrupt_before` / `interrupt_after` on a tool node (or `"*"`) | `approval.required` = that node's tools |
| LangGraph | `recursion_limit` | `limits.max_steps` |
| LangGraph | several agent nodes; `supervisor` | `roles.actors`, `capabilities.multi_agent`; `roles.orchestrators` |
| AutoGen | `human_input_mode: ALWAYS` on the tool-executing agent | `approval.required` = its `function_map` / tools |
| AutoGen | `max_consecutive_auto_reply`, `max_turns`, `max_round` | `limits.max_steps` (largest) |
| AutoGen | group chat manager / selector; participants with tools | `roles.orchestrators`; `roles.actors` |
| CrewAI | task `human_input: true` | `approval.required` = the task's tools, else its agent's tools |
| CrewAI | agent `max_iter`; agent `max_rpm` | `limits.max_steps`; `rateLimits` per tool of that agent (`maxCalls` = rpm, `perSeconds` = 60) |
| CrewAI | `process: hierarchical` / `manager_agent` | `roles.orchestrators` |

The mappings are deliberately conservative: a fact the framework config does not state is not invented. A
human-in-the-loop call inside tool code (e.g. LangGraph `interrupt()` in a tool body) is not visible in the
configuration and must be published by hand.

## 9. Versioning

The URI carries the major version. Additive, optional fields MAY be added within `v1`; removing a field,
changing its meaning or its type requires `v2` and a new URI. A consumer that knows `v1` MUST NOT interpret a
`v2` entry as `v1`.

## 10. Security considerations

* The facts are self-asserted by the agent owner. An owner can under-declare (e.g. omit a destructive tool from
  `approval.required`) to make checks pass. Reviewers SHOULD compare the declaration with MCP annotations and
  the derived facts of section 7/8, and MAY require a signed AgentCard (A2A AgentCard signatures).
* `params` MUST NOT contain secrets, credentials or personal data. `fairness` values are synthetic test tokens.
* Consumers SHOULD treat the AgentCard as untrusted input: validate against the schema before use and never
  evaluate field values as code or patterns beyond the documented suffix matching.

## 11. Privacy considerations

`dataClassification`, `disclosureTools` and `exportTools` name kinds of data and tools, not data. Traces used to
check them can contain personal data; their retention is outside this document.

## 12. Relation to other work

* **A2A** defines the extension mechanism (`capabilities.extensions[]`). **MCP** tool annotations cover
  read-only / destructive / idempotent / open-world hints; this extension adds what they do not (approval,
  data classes, rates, compensation, roles). **OpenTelemetry GenAI** semantic conventions carry the observed
  behaviour the facts are checked against.
* Proposed upstreaming: approval and data-class facts as MCP annotations; the approval span and tool reason as
  OTel GenAI attributes. When those exist, the matching field here becomes an alias.

## 13. Open questions

1. Should `approval.required` accept argument-level conditions (e.g. refunds above an amount) without becoming
   an expression language?
2. Should derived facts be publishable with a `derivedFrom` marker inside `params`, instead of out of band?
3. Is a registry of `dataClassification` kinds (with reference detectors) wanted?
4. How should facts for agents a card delegates to (A2A remote agents) be composed?
