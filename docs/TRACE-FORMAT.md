# Trace format 1.0.0

This page lists every trace attribute that agentest checks read: the 165 tests, including T1-020 and
T1-021, and the opt-in New tests NT-001 to NT-030 and NT-039 to NT-043. It says who provides each attribute, whether it is required, its type,
and which checks read it. The JSON Schema
[`trace-format.schema.json`](../src/agentest/standards/schemas/trace-format.schema.json) carries the same list and
checks the attribute types of an OTLP/JSON trace.

**Status: format 1.0.0, decisions D1–D9 approved 18 Nov 2026** (see [Decisions](#decisions-d1d9)). The names and
encodings below describe what the code reads today, plus the canonical names and read aliases the decisions set.
Nothing here changes a check or a verdict. Attributes planned for Phase 2 (format 1.1) are listed separately in
[Planned for 1.1](#planned-for-11-phase-2) and are not part of the 1.0.0 schema.

## How agentest reads a trace

- Input is OTLP: OTLP/JSON (`.json`, one export per line in `.jsonl`) or OTLP/protobuf (`.pb`). Spans of one
  `traceId` are one run. Spans are read in start-time order.
- The **root span** (no parent) holds the run-level facts: input, final answer, input id, repetition, final state,
  test-side labels and the `agentest.task.*` declarations.
- **Tool spans** have `gen_ai.operation.name = execute_tool`. **Model spans** have `chat`, `text_completion` or
  `generate_content`. **Agent spans** have `invoke_agent`.
- **Records** are spans or events with a fixed name (for example `agentest.approval`); see [Records](#records).
- Attribute names follow the OpenTelemetry GenAI semantic conventions pinned in
  [`semconv.yaml`](../src/agentest/standards/semconv.yaml) (semconv 1.42.0). Older GenAI versions and the other
  instrumentation styles listed there are mapped to the current names when a trace is read; a current name already on
  a span is never overwritten.
- Names outside the conventions use the `agentest.` prefix (see also [EXTENSION.md](standards/EXTENSION.md)).
- Run-level attributes (`agentest.trace_format.version`, `agentest.run.id`, `agentest.source.start_time_unix_nano`)
  may sit on the resource or on the root span.

## Who provides an attribute

| Class | Meaning | Examples |
|:--|:--|:--|
| auto-captured | OpenTelemetry GenAI instrumentation, or an agentest importer, records it from what the framework already does. The team adds nothing. | `gen_ai.tool.name`, `gen_ai.input.messages`, `agentest.run.rep` |
| team-declared | The team or the test set states it before the run: policy, budgets, expected values, test-side labels. On the trace it sits on the root span (`agentest.task.*`, `agentest.input.*`) or on a labelled step; policy that holds for every run sits beside the trace in the AgentCard governance extension and the MCP tool list. | `agentest.task.budget.latency_s`, `agentest.test.canaries`, `approval.required` |
| agent-output | Recorded at run time by the agent or by the system it acts on. Standard instrumentation does not record it, so the agent, its application or a connector must emit it. | `agentest.approval` spans, `agentest.final_state`, `agentest.decision.*` |

## Required and optional

- **required**: without it a span cannot be typed. Only `gen_ai.operation.name` is required; the OTLP span fields
  `traceId`, `spanId`, `name`, `startTimeUnixNano` and `endTimeUnixNano` are required by OTLP itself.
- **required-if *record***: required when that record is present (for example `agentest.approval.action` on an
  `agentest.approval` span). A record without it is not a valid record; the schema rejects it.
- **optional**: everything else. A check whose attribute is missing reports `n/a`, never `pass`. Where a default
  is used it is named in the Notes column.

## Encoding

- Scalars use the OTLP value of their type: `stringValue`, `intValue` (OTLP/JSON writes it as a string),
  `doubleValue`, `boolValue`.
- Lists of scalars (`string[]`): emit an OTLP `arrayValue` of strings. The reader also accepts a JSON list in a
  string, and the NT checks accept a comma-separated string. (The importer still writes JSON strings; that is
  unchanged so imported traces stay byte-identical.)
- Objects and nested lists (`JSON …`): emit a JSON string. The reader also accepts OTLP `kvlistValue` /
  `arrayValue`.
- Grouping keys (a persona attribute, a variant, a fault kind, an input channel) are flat scalar attributes, one key
  each, never fields inside a JSON object, so runs can be grouped and combined without parsing.
- `agentest.final_state` may carry sets and bytes as `{"$set": [...]}`, `{"$frozenset": [...]}`, `{"$bytes": "..."}`.
- Unknown attributes are allowed and ignored.

## Counts

All attributes on this page (records and fields declared beside the trace are counted separately below):

| Provided by | Required (incl. required-if) | Optional | Total |
|:--|--:|--:|--:|
| auto-captured | 2 | 19 | 21 |
| team-declared | 1 | 50 | 51 |
| agent-output | 13 | 87 | 100 |
| **all** | 16 | 156 | 172 |

On main today:

| Provided by | Required (incl. required-if) | Optional | Total |
|:--|--:|--:|--:|
| auto-captured | 2 | 19 | 21 |
| team-declared | 0 | 7 | 7 |
| agent-output | 3 | 15 | 18 |
| **all** | 5 | 41 | 46 |

Introduced by the NT batches (on the batch branches, not yet on main):

| Provided by | Required (incl. required-if) | Optional | Total |
|:--|--:|--:|--:|
| auto-captured | 0 | 0 | 0 |
| team-declared | 1 | 42 | 43 |
| agent-output | 9 | 66 | 75 |
| **all** | 10 | 108 | 118 |

## Attributes on main

"Read by" lists the checks found by a static scan of the check code (a check that reads every tool call, for example,
reads `gen_ai.tool.name`). Long lists are cut and show the number of checks.

| Attribute | Where | Type | Provided by | Required | Read by | Notes |
|:--|:--|:--|:--|:--|:--|:--|
| `gen_ai.operation.name` | every span | string: invoke_agent \| execute_tool \| chat \| text_completion \| generate_content | auto-captured | required | all checks (span type) | Without it a span is only counted for timing. |
| `gen_ai.tool.name` | tool span | string | auto-captured | required-if tool span | T1-002, T1-004, T1-005, T1-006, T1-007, T1-008, T1-009, T1-010, T1-011, T1-012, T1-013, T1-014, T1-015, T1-016 … (126 checks) | Falls back to the span name `execute_tool <name>`. |
| `gen_ai.tool.call.arguments` | tool span | JSON object (string) | auto-captured | optional | T1-002, T1-004, T1-006, T1-008, T1-010, T1-011, T1-012, T1-014, T1-015, T1-016, T1-017, T1-018, T1-020, T1-021 … (68 checks) | Missing → `{}`; a non-JSON value is kept as `{"_raw": …}`. |
| `gen_ai.tool.call.result` | tool span | string or JSON | auto-captured | optional | T1-002, T1-004, T1-005, T1-008, T1-012, T1-014, T1-015, T1-016, T1-017, T1-018, T1-021, T2-006, T2-007, T2-008 … (52 checks) |  |
| `gen_ai.tool.call.id` | tool span | string | auto-captured | optional | NT-015, NT-016, NT-020, NT-021, NT-022, NT-024, NT-029 | Joins `tool_call` message parts to tool spans. |
| `gen_ai.agent.name` | agent span, tool span | string | auto-captured | optional | T3-002, T3-007, T3-009, T3-011, X-005, NT-013, NT-014 | Tool span: the acting agent. Agent span: the agent invoked. |
| `gen_ai.conversation.id` | root span (or any span) | string | auto-captured | optional | T1-017, T1-020, T6-001, T6-004, T6-005, T6-006, T6-008, T6-012, T6-013, T6-014, NT-001, NT-002, NT-003, NT-004 … (19 checks) | Session id (D9): groups the turns of one conversation; fallback for `agentest.input.id`. Also read as: `session.id`. |
| `gen_ai.input.messages` | root, model and agent spans | JSON list of messages (string) | auto-captured | optional | T1-001, T1-002, T1-003, T1-004, T1-006, T1-007, T1-011, T1-014, T1-016, T1-017, T1-018, T1-020, T2-003, T2-005 … (50 checks) | User input, turn boundaries and attachments. Older GenAI message events are mapped too. Also read as: `gen_ai.prompt`. |
| `gen_ai.output.messages` | root and model spans | JSON list of messages (string) | auto-captured | optional | T1-002, T1-005, T1-014, T1-018, T1-020, T1-021, T2-005, T2-009, T4-001, T4-005, T4-006, T4-007, T4-009, T4-010 … (47 checks) | Final answer (root, else last model span), model replies, parallel tool-call batches. Also read as: `gen_ai.completion`. |
| `gen_ai.usage.input_tokens` | model span | int | auto-captured | optional | NT-002 | Also read as: `gen_ai.usage.prompt_tokens`. |
| `gen_ai.usage.output_tokens` | model span | int | auto-captured | optional | NT-002 | Also read as: `gen_ai.usage.completion_tokens`. |
| `error.type` | tool span, root span | string | auto-captured | optional | T1-002, T1-004, T1-005, T1-006, T1-007, T1-008, T1-009, T1-010, T1-011, T1-012, T1-013, T1-014, T1-015, T1-016 … (126 checks) | Present (or span status ERROR) = the call or the run failed. |
| `gen_ai.evaluation.score.label` | event gen_ai.evaluation.result (root) | string: pass \| fail \| … | team-declared | optional | T1-001, T1-002, T1-003, T1-018, T7-009 | Harness or oracle verdict on the run (success signal). |
| `gen_ai.evaluation.score.value` | event gen_ai.evaluation.result (root) | double | team-declared | optional | T1-001, T1-002, T1-003, T1-018, T7-009 | Carried with the label; checks read the label. |
| `user.roles` | root span (or any span) | string[] | agent-output | optional | T5-016, NT-022 | Standard OTel registry attribute: roles of the session user (D1 canonical). Also read as: `enduser.roles`, `agentest.auth.role`. |
| `agentest.input.id` | root span | string | auto-captured | optional | all checks (groups runs of one input) | Fallback: `gen_ai.conversation.id`, then the trace id. |
| `agentest.run.rep` | root span | int | auto-captured | optional | T1-002, T1-005, T1-006, T1-011, T1-018, T2-001, T2-003, T2-004, T2-005, T2-006, T2-007, T2-008, T2-009, T2-010 … (39 checks) | Missing → 0. |
| `agentest.duration_s` | root span | double | auto-captured | optional | X-007, NT-001 | Missing → root span end − start. |
| `agentest.error.message` | root span | string | auto-captured | optional | T1-001, T1-002, T1-003, T1-005, T1-018, X-008 | Run-level error text. |
| `agentest.handoff.source` | agent span | string | auto-captured | optional | T3-007, T3-009, T3-011, X-005, NT-013, NT-014 | On the invoked agent's span: who handed off. |
| `agentest.source.time_s` | tool span | double | auto-captured | optional | T2-014 | Original native-log timestamp (importer). |
| `agentest.final_state` | root span | JSON object (string; typed $set/$frozenset/$bytes) | agent-output | optional | T1-001, T1-002, T1-003, T1-018, T1-020, T4-001, T4-005, T4-006, T4-009, T4-010, T4-011, T4-012, T4-013, T4-014 … (24 checks) | Observed end state in the system of record. |
| `agentest.outputs` | root span | JSON list (string) | agent-output | optional | T7-014, X-019 | Structured outputs (importer `observations.outputs`). |
| `agentest.citations` | root span | JSON list (string) | agent-output | optional | T6-007, T6-009 | Sources or memory items the agent says it used. |
| `agentest.tool.reason` | tool span | string | agent-output | optional | T5-015, X-003, NT-015 | The agent's stated reason for the call (or a `reason` argument). |
| `agentest.approval.action` | span agentest.approval | string | agent-output | required-if approval span | T1-021, T2-004, T2-011, T2-012, T3-001, T3-002, T3-003, T3-004, T3-005, T3-006, T3-010, T3-012, T3-013, T3-014 … (18 checks) | Tool or action decided on. |
| `agentest.approval.granted` | span agentest.approval | bool | agent-output | required-if approval span | T1-021, T2-004, T2-011, T2-012, T3-001, T3-002, T3-003, T3-004, T3-005, T3-006, T3-010, T3-012, T3-013, T3-014 … (18 checks) |  |
| `agentest.approval.approver` | span agentest.approval | string | agent-output | optional | T3-002, T3-004, T3-012 |  |
| `agentest.approval.target` | span agentest.approval | string | agent-output | optional | T3-003, T3-010, X-016, X-017 | Object acted on. |
| `agentest.approval.policy_version` | span agentest.approval | string | agent-output | optional | T3-006 |  |
| `agentest.approval.reason` | span agentest.approval | string | agent-output | optional | T1-021, T3-004, T3-012 |  |
| `agentest.approval.kind` | span agentest.approval | string (e.g. consent, step_up, mfa) | agent-output | optional | NT-027 | Also read by the opt-in RAI addition T3-018. |
| `agentest.approval.data_class` | span agentest.approval | string | agent-output | optional | none (report only) | Read only by the opt-in RAI addition T3-018. D2 canonical name; the reader reads `agentest.approval.dataClass` today, so emit that name until the read alias lands. Also read as: `agentest.approval.dataClass`. |
| `agentest.approval.purpose` | span agentest.approval | string | agent-output | optional | none (report only) | Read only by the opt-in RAI addition T3-018. |
| `agentest.state_change.kind` | event agentest.state_change (root) | string: executed \| pending \| unapproved \| diff | agent-output | required-if state_change event | T1-002, T1-004, T1-006, T1-007, T1-008, T1-011, T1-012, T1-013, T1-018, T2-003, T2-004, T2-012, T3-001, T3-003 … (33 checks) |  |
| `agentest.state_change.effect` | event agentest.state_change (root) | string | agent-output | optional | T1-002, T1-004, T1-006, T1-007, T1-008, T1-011, T1-012, T1-013, T1-018, T2-003, T2-004, T2-012, T3-001, T3-003 … (33 checks) |  |
| `agentest.state_change.data` | event agentest.state_change (root) | string or JSON | agent-output | optional | T1-002, T1-004, T1-006, T1-007, T1-008, T1-011, T1-012, T1-013, T1-018, T2-003, T2-004, T2-012, T3-001, T3-003 … (33 checks) |  |
| `agentest.input.families` | root span | string[] | team-declared | optional | T1-001, T1-003, T1-006, T1-007, T1-011, T1-013, T2-003, T2-005, T2-011, T3-001, T3-003, T3-005, T3-010, T3-013 … (42 checks) | Test-side label: input families (injection, empty, …). |
| `agentest.input.injected` | root span | string[] | team-declared | optional | T4-001, T4-005, T4-006, T4-009, T4-010, T4-011, T4-012, T4-013, T4-014, T4-016, T6-005 | Test-side label: the injected directive text. |
| `agentest.input.relations` | root span | JSON list (string) | team-declared | optional | T7-001, T7-002, T7-003, T7-004, T7-005, T7-006, T7-007, T7-011, T7-012, T7-013 | Metamorphic relations between inputs. |
| `agentest.test.canaries` | root span | string[] | team-declared | optional | T4-001, T4-002, T4-003, T4-005, T4-006, T4-009, T4-010, T4-011, T4-013, T4-014, T4-016, T5-005, T5-017, T6-011 … (15 checks) | Planted secrets that must not leak. |
| `agentest.task.initial_state` | root span | JSON object (string) | team-declared | optional | T1-020 | State before the undo (D2 canonical name). Also read as: `agentest.undo.before`. |
| `agentest.trace_format.version` | resource (or root span) | string (semver) | auto-captured | optional | none (report only) | D5: trace format version. Missing → 1.0.0. Phase 2 attributes are 1.1. |
| `agentest.run.id` | resource (or root span) | string | auto-captured | optional | none (report only) | D9: joins the traces of one run when agents export separate traces. Missing → one trace is one run. |
| `user.id` | root span (or any span) | string | agent-output | optional | none (report only) | D9: subject across sessions (standard OTel registry name). |
| `agentest.source.start_time_unix_nano` | resource (or root span) | int | auto-captured | optional | none (report only) | D9: native start time of an imported run. The replay clock of imported traces is unchanged; cross-trace time checks read this. |

## Attributes introduced by the New tests

These are read by the New tests (`NT-001` to `NT-030`) and documented on the New tests pages
([docs/new-tests/](new-tests/README.md), including `b1.md` to `b4.md`). They ship in the current tree.

### NT batch 1 (#184): NT-001 to NT-009

| Attribute | Where | Type | Provided by | Required | Read by | Notes |
|:--|:--|:--|:--|:--|:--|:--|
| `agentest.task.id` | root span | string | team-declared | optional | NT-001, NT-002, NT-003, NT-004, NT-005, NT-006, NT-007, NT-008, NT-009 | Groups repeated runs of one task; fallback `agentest.input.id`. |
| `agentest.task.budget.latency_s` | root span | double | team-declared | optional | NT-001 |  |
| `agentest.task.budget.tokens` | root span | int | team-declared | optional | NT-002 |  |
| `agentest.task.budget.cost` | root span | double | team-declared | optional | NT-002 |  |
| `agentest.usage.cost` | model span (any span) | double | agent-output | optional | NT-002, NT-013 | Spend of a call; not in the GenAI conventions. |
| `agentest.task.autonomy_level` | root span | double (0..1, or percent) | team-declared | optional | NT-003 |  |
| `agentest.task.autonomy_tolerance` | root span | double | team-declared | optional | NT-003 | Missing → 0.05. |
| `agentest.step.human_input` | tool span (any span) | bool | agent-output | optional | NT-003, NT-013, NT-014 | The step had human help. |
| `agentest.step.expected_tool` | tool span | string | team-declared | optional | NT-004 | Label: the right tool for this step. |
| `agentest.step.acceptable_tools` | tool span | string[] | team-declared | optional | NT-004 |  |
| `agentest.task.allowed_actions` | root span | string[] | team-declared | optional | NT-005 |  |
| `agentest.input.attack` | root span | bool | team-declared | optional | NT-005 | Run is an attack input; left to the injection checks. |
| `agentest.tool.kind` | tool span | string: page_snapshot \| knowledge_lookup \| framework_output | team-declared or importer | optional | NT-006, NT-017, T5-001, T5-018 | `framework_output` marks a framework-owned structured-result / output tool; T5-001 and T5-018 do not treat it as undeclared. Also introduced by batch 3. |
| `agentest.output.structured` | root span | JSON object (string) | agent-output | optional | NT-006, NT-009, NT-017 | Else a final answer that is a JSON object. D2 canonical name. Also read as: `agentest.output`. |
| `agentest.task.extracted` | root span | string[] | team-declared | optional | NT-006 |  |
| `agentest.ui.action` | any span | string: click \| submit \| … | agent-output | required-if UI step | NT-007, NT-008 |  |
| `agentest.ui.element_id` | any span | string | agent-output | optional | NT-007 |  |
| `agentest.ui.expected_element_id` | any span | string | team-declared | optional | NT-007 |  |
| `agentest.form.id` | form span | string | agent-output | required-if form span | NT-008 |  |
| `agentest.form.action` | form span | string: submit \| … | agent-output | optional | NT-008 | Else `agentest.ui.action`. |
| `agentest.form.values` | form span | JSON object (string) | agent-output | optional | NT-008 |  |
| `agentest.form.validation_errors` | form span | JSON list or object (string) | agent-output | optional | NT-008 |  |
| `agentest.form.step` | form span | int | agent-output | optional | NT-008 |  |
| `agentest.form.steps_total` | form span | int | agent-output | optional | NT-008 |  |
| `agentest.task.expected_form` | root span | JSON object (string) | team-declared | optional | NT-008 |  |
| `agentest.task.form_steps` | root span | JSON object (string) | team-declared | optional | NT-008 |  |
| `agentest.task.output_mapping` | root span | JSON object (string) | team-declared | optional | NT-009 |  |
| `agentest.api.response_status` | tool span | string: ok \| partial \| malformed \| invalid \| truncated | agent-output | optional | NT-009 |  |
| `agentest.output.flagged` | root span | string[] | agent-output | optional | NT-009 | Fields or tools the agent reported as unusable. |

### NT batch 2 (#183): NT-010 to NT-014, NT-027

| Attribute | Where | Type | Provided by | Required | Read by | Notes |
|:--|:--|:--|:--|:--|:--|:--|
| `agentest.a2a.message_id` | any span | string | agent-output | required-if agent-to-agent message | NT-010, NT-011, NT-012 |  |
| `agentest.a2a.direction` | any span | string: send \| receive | agent-output | optional | NT-010, NT-011, NT-012 | Else span name ending `.send` / `.receive`. |
| `agentest.a2a.payload` | any span | string or JSON | agent-output | optional | NT-010, NT-011 |  |
| `agentest.a2a.payload_hash` | any span | string (sha256 hex, optional `sha256:` prefix) | agent-output | optional | NT-010 |  |
| `agentest.a2a.transform` | any span | string | agent-output | optional | NT-010 | Declared, intended change on this hop. |
| `agentest.a2a.message_type` | any span | string: request \| accept \| result \| subgoal \| handoff \| escalation | agent-output | optional | NT-011, NT-012, NT-013, NT-014 |  |
| `agentest.a2a.fields` | any span | JSON object (string) | agent-output | optional | NT-011 |  |
| `agentest.a2a.ack_of` | any span | string | agent-output | optional | NT-012 |  |
| `agentest.task.handover_schema` | root span | JSON object (string) | team-declared | optional | NT-011 |  |
| `agentest.task.ack_within_s` | root span | double | team-declared | optional | NT-012 |  |
| `agentest.step.kind` | any span | string: handoff \| stop \| escalate | agent-output | optional | NT-013, NT-014 |  |
| `agentest.task.limits` | root span | JSON object (string) | team-declared | optional | NT-013 |  |
| `agentest.task.autonomy_window_s` | root span | double | team-declared | optional | NT-014 |  |
| `agentest.task.autonomy_window_tolerance_s` | root span | double | team-declared | optional | NT-014 | Missing → 0. |
| `agentest.task.step_up_tools` | root span | string[] | team-declared | optional | NT-027 | With governance `approval.stepUp`. |

### NT batch 3 (#185): NT-015 to NT-019, NT-028, NT-029

| Attribute | Where | Type | Provided by | Required | Read by | Notes |
|:--|:--|:--|:--|:--|:--|:--|
| `agentest.step.high_impact` | tool span | bool | team-declared | optional | NT-015 |  |
| `agentest.step.rationale` | tool span | JSON object or string | agent-output | optional | NT-015, NT-016 |  |
| `agentest.step.rule` | tool span | string | agent-output | optional | NT-016 |  |
| `agentest.probe.kind` | probe span | string: why | team-declared | required-if probe span | NT-016 |  |
| `agentest.probe.target` | probe span | string (call id or tool name) | team-declared | optional | NT-016 | Missing → last call before the probe. |
| `agentest.probe.reply` | probe span | string | agent-output | optional | NT-016 | Else the span's `gen_ai.output.messages`. |
| `agentest.task.probe_latency_s` | root span | double | team-declared | optional | NT-016 |  |
| `agentest.task.knowledge_fields` | root span | string[] | team-declared | optional | NT-017 |  |
| `agentest.task.knowledge_tools` | root span | string[] | team-declared | optional | NT-017 |  |
| `agentest.decision.id` | span agentest.decision | string | agent-output | optional | NT-018, NT-019, NT-028, NT-029 | Missing → span id. |
| `agentest.decision.outcome` | span agentest.decision | string | agent-output | required-if decision record | NT-018, NT-019, NT-028, NT-029 | Any span carrying it is a decision record. |
| `agentest.decision.consequential` | span agentest.decision | bool | agent-output | optional | NT-018, NT-019 |  |
| `agentest.decision.inputs` | span agentest.decision | JSON object (string) | agent-output | optional | NT-018, NT-028, NT-029 |  |
| `agentest.decision.criteria` | span agentest.decision | JSON list or object (string) | agent-output | optional | NT-028, NT-029 |  |
| `agentest.decision.reasons` | span agentest.decision | JSON list (string) | agent-output | optional | NT-018, NT-028 |  |
| `agentest.decision.rule` | span agentest.decision | string | agent-output | optional | NT-029 |  |
| `agentest.decision.outputs` | span agentest.decision | JSON (string) | agent-output | optional | NT-029 | Missing → the outcome. |
| `agentest.decision.derivations` | span agentest.decision | JSON object (string) | agent-output | optional | NT-029 |  |
| `agentest.decision.sampled` | span agentest.decision | bool | team-declared | optional | NT-029 |  |
| `agentest.task.consequential_outcomes` | root span | string[] | team-declared | optional | NT-018, NT-019 |  |
| `agentest.task.review_sample` | root span | string[] | team-declared | optional | NT-029 |  |
| `agentest.task.notice_template` | root span | JSON object (string) | team-declared | optional | NT-019 |  |
| `agentest.notice` | any span | JSON object (string): decision_id, sections, fields | agent-output | optional | NT-019 | Or an `agentest.notice` span with `agentest.notice.*` attributes. |
| `agentest.notice.decision_id` | span agentest.notice | string | agent-output | optional | NT-019 |  |
| `agentest.notice.sections` | span agentest.notice | string[] | agent-output | optional | NT-019 |  |
| `agentest.notice.fields` | span agentest.notice | JSON object (string) | agent-output | optional | NT-019 |  |

### NT batch 4 (#186): NT-020 to NT-026, NT-030

| Attribute | Where | Type | Provided by | Required | Read by | Notes |
|:--|:--|:--|:--|:--|:--|:--|
| `agentest.data.categories` | tool span | string[] | agent-output | optional | NT-020, NT-022 |  |
| `agentest.data.operation` | tool span | string: read \| write \| update \| delete \| create | agent-output | optional | NT-020, NT-022 | Missing → read. |
| `agentest.access.outcome` | tool span | string: allowed \| denied \| blocked \| refused | agent-output | optional | NT-020, NT-021, NT-022, NT-024 | Else span status. |
| `agentest.access_log.ref` | span agentest.access_log | string (call id or span id) | agent-output | required-if access-log span | NT-020 |  |
| `agentest.access_log.actor` | span agentest.access_log | string | agent-output | optional | NT-020 |  |
| `agentest.access_log.category` | span agentest.access_log | string | agent-output | optional | NT-020 |  |
| `agentest.access_log.purpose` | span agentest.access_log | string | agent-output | optional | NT-020 |  |
| `agentest.task.pii_categories` | root span | string[] | team-declared | optional | NT-020 |  |
| `agentest.data.destination_region` | tool span | string | agent-output | optional | NT-021 |  |
| `agentest.task.disallowed_regions` | root span | string[] | team-declared | optional | NT-021 | Or governance `privacy.disallowedRegions`. |
| `agentest.data.sensitive` | tool span | bool | agent-output | optional | NT-022 |  |
| `agentest.task.sensitive_categories` | root span | string[] | team-declared | optional | NT-022 | Missing → sensitive, pii. |
| `agentest.task.privileged_roles` | root span | string[] | team-declared | optional | NT-022 | Or governance `roles.adminRoles`. |
| `agentest.data.resource` | tool span | string | agent-output | optional | NT-022 |  |
| `agentest.data.subject_id` | tool span | string | agent-output | optional | NT-022, NT-024 |  |
| `agentest.data.purpose` | tool span | string | agent-output | optional | NT-024 |  |
| `agentest.task.ai_disclosure_required` | root span | bool | team-declared | optional | NT-023 |  |
| `agentest.task.ai_disclosure_text` | root span | string | team-declared | optional | NT-023 |  |
| `agentest.reply.ai_disclosure` | model span | bool | agent-output | optional | NT-023 |  |
| `agentest.user_setting.key` | span agentest.user_setting | string | agent-output | required-if user-setting span | NT-024 |  |
| `agentest.user_setting.value` | span agentest.user_setting | string or JSON | agent-output | optional | NT-024 |  |
| `agentest.user_setting.subject_id` | span agentest.user_setting | string | agent-output | optional | NT-024 |  |
| `agentest.user_setting.state_path` | span agentest.user_setting | string (dotted path into final state) | agent-output | optional | NT-024 |  |
| `agentest.user_setting.blocks_purposes` | span agentest.user_setting | string[] | agent-output | optional | NT-024 |  |
| `agentest.dsar.id` | spans agentest.dsar.request / .completion | string | agent-output | required-if DSAR span | NT-025 |  |
| `agentest.dsar.type` | span agentest.dsar.request | string: access \| correction \| deletion | agent-output | optional | NT-025 |  |
| `agentest.dsar.status` | span agentest.dsar.completion | string | agent-output | optional | NT-025 | Missing → completed. |
| `agentest.task.dsar_sla_s` | root span | double, or JSON object by type | team-declared | optional | NT-025 |  |
| `agentest.artifact.generated` | any span | bool | agent-output | optional | NT-026 |  |
| `agentest.artifact.ai_label` | any span | string | agent-output | optional | NT-026 | Default label attribute; `agentest.task.ai_label` can name another. |
| `agentest.artifact.id` | any span | string | agent-output | optional | NT-026 | Names the artifact in the evidence. |
| `agentest.task.ai_label` | root span | string or JSON object {field, value} | team-declared | optional | NT-026 |  |
| `agentest.fault.injected` | injected-fault span | bool | agent-output | optional | NT-038, NT-040 | Set by the fault harness on the faulted span. |
| `agentest.fault.id` | injected-fault span | string | agent-output | optional | NT-038 | Alerts refer to it through `agentest.alert.ref`. |
| `agentest.fault.kind` | injected-fault span | string (timeout, error, malformed, hostile, env_change, overload, fuzz, exploit) | agent-output | optional | NT-038, NT-040 | NT-038 reads `exploit` as the privacy fault; NT-040 reads `fuzz` on tool spans. |
| `agentest.alert.ref` | alert record | string (= `agentest.fault.id`) | agent-output | required-if alert | NT-038 | |
| `agentest.alert.kind` | alert record | string | agent-output | optional | NT-038 | Not required by NT-038. |
| `agentest.alert.severity` | alert record | string | agent-output | optional | NT-038 | Not required by NT-038. |
| `agentest.task.detect_within_s` | root span | number (seconds) | team-declared | optional | NT-038 | Detection window for privacy alerts. |
| `agentest.consent.subject_id` | span agentest.consent.revoke | string | agent-output | required-if revocation | NT-030 |  |
| `agentest.consent.action` | any span | string: revoke | agent-output | optional | NT-030 | Alternative to the span name. |
| `agentest.snapshot.kind` | span agentest.snapshot | string: store \| training_queue | agent-output | required-if snapshot span | NT-030 |  |
| `agentest.snapshot.data` | span agentest.snapshot | JSON (string) | agent-output | optional | NT-030 |  |
| `agentest.task.store_path` | root span | string (dotted path) | team-declared | optional | NT-030 |  |
| `agentest.task.training_queue_path` | root span | string (dotted path) | team-declared | optional | NT-030 |  |

### NT batch 5: NT-037, NT-039, NT-040, NT-041, NT-042, NT-043

These names are read by the opt-in checks on [docs/new-tests/b5.md](new-tests/b5.md). They are not part of the published test count. `agentest.environment.change` is still listed under [Planned for 1.1](#planned-for-11-phase-2) because it is not in the 1.0.0 schema; the check reads the span when a trace carries it. Unknown attributes stay allowed. Absent declarations are `n/a`.

| Attribute | Where | Type | Provided by | Required | Read by | Notes |
|:--|:--|:--|:--|:--|:--|:--|
| `gen_ai.request.model` | root or chat span | string | agent-output | optional | NT-039 | `gen_ai.response.model` also counts. |
| `gen_ai.request.seed` | root or chat span | int | agent-output | optional | NT-039 | Scopes the set when any run records it. |
| `agentest.prompt.version` | root or chat span | string | team-declared | optional | NT-039 | Prompt version used by the run. |
| `agentest.context.ids` | root or chat span | string[] | agent-output | optional | NT-039 | Empty lists count as missing. |
| `agentest.replay.of` | root or chat span | string (trace id) | agent-output | optional | NT-039 | Trace id of the original run. |
| `agentest.environment.change.kind` | span agentest.environment.change | string: write \| create \| update \| put \| produce \| read \| get \| load \| fetch \| consume \| open | agent-output | optional | NT-041 | Omitted kind: a new ref is a write; a ref an earlier trial wrote is a read. |
| `agentest.environment.change.ref` | span agentest.environment.change | string | agent-output | optional | NT-041 | Artefact id. |
| `agentest.fault.target` | injected-fault span | string | agent-output | optional | NT-040 | Names the faulted tool when present. |
| `server.address` | tool span or access span | string | agent-output | optional | NT-037, NT-040 | Observed host. Judged only when a host allow-list is declared. |
| `url.full` | tool span | string | agent-output | optional | NT-040 | Observed full URL. Host checked when a host allow-list is declared. |
| `file.path` | tool span or access span | string | agent-output | optional | NT-037, NT-040 | Observed path. Normalised before the allow-list test. |
| `process.executable.name` | tool span or access span | string | agent-output | optional | NT-037 | Observed process name. |
| `agentest.task.skill` | root span | string | team-declared | optional | NT-042 | Links a run to an AgentCard skill id. |
| `agentest.task.budget.tool_errors` | root span | int | team-declared | optional | NT-043 | Ignored when absent. |
| `agentest.task.budget.repeat_calls` | root span | int | team-declared | optional | NT-043 | Ignored when absent. |

## Records

Spans and events with a fixed name. Their own attributes are in the tables above.

| Kind | Name | Provided by | Introduced by | Meaning |
|:--|:--|:--|:--|:--|
| span | `agentest.approval` | agent-output | main | human or policy decision on an action |
| event | `agentest.state_change` | agent-output | main | durable effect in the system of record (root span event) |
| event | `gen_ai.evaluation.result` | team-declared | main | standard GenAI event: harness or oracle verdict |
| span | `agentest.human_input` | agent-output | NT batch 1 (#184) | a person stepped in |
| span | `agentest.handoff` | agent-output | NT batch 2 (#183) | control handed to another agent or a person |
| span | `agentest.stop` | agent-output | NT batch 2 (#183) | the agent stopped |
| span | `agentest.decision` | agent-output | NT batch 3 (#185) | decision record |
| span | `agentest.notice` | agent-output | NT batch 3 (#185) | decision notice sent to the subject |
| span | `agentest.access_log` | agent-output | NT batch 4 (#186) | access-log entry for a data read |
| span | `agentest.user_setting` | agent-output | NT batch 4 (#186) | user changed a data-control setting |
| span | `agentest.dsar.request` | agent-output | NT batch 4 (#186) | data-subject request received |
| span | `agentest.dsar.completion` | agent-output | NT batch 4 (#186) | data-subject request completed |
| span | `agentest.consent.revoke` | agent-output | NT batch 4 (#186) | consent revoked |
| span | `agentest.snapshot` | agent-output | NT batch 4 (#186) | store or training-queue snapshot |
| record | `agentest.alert` | agent-output | NT batch 5 (#215) | alert raised for an injected fault (span, span event or log record) |

A form step, a UI step, a probe or an agent-to-agent message is any span carrying the matching attributes
(`agentest.form.*`, `agentest.ui.*`, `agentest.probe.*`, `agentest.a2a.*`); its name is free.

## Declared beside the trace

Policy that holds for every run is declared once, outside the trace: in the AgentCard governance extension
`urn:agentest:a2a-ext:governance:v1` ([EXTENSION.md](standards/EXTENSION.md),
[schema](../src/agentest/standards/schemas/governance-extension.schema.json)) and in the MCP `tools/list` result
(annotations and `inputSchema`). All of it is team-declared and optional; a check whose fact is absent reports `n/a`
(MCP annotations take their MCP defaults when a tool is not listed).

| Field | Declared in | Read by |
|:--|:--|:--|
| `approval.required` | governance | T2-004, T2-012, T3-001, T3-003, T3-004, T3-005, T3-006, T3-010, T3-013, T3-014, T5-014, T6-005, NT-015 |
| `approval.hostGated` | governance | T2-004, T2-012, T3-001, T3-005, T3-013 |
| `approval.ttlSeconds` | governance | T3-014 |
| `approval.stepUp` | governance (introduced by NT batch 2) | NT-027 |
| `dataClassification.restricted` | governance | T5-004, X-020 |
| `recipients.allow` | governance | T1-004, T4-003 |
| `limits.*` | governance | T5-006, X-005, X-006, X-007 |
| `network.allowHosts` | governance | T4-002, T5-005, T5-017 |
| `mutuallyExclusive` | governance | T5-013 |
| `prerequisites` | governance | T1-008, T1-012, T2-001, T2-002, T2-005, T2-007, T2-009, T2-010, T2-013 |
| `disclosureTools` | governance | T2-005 |
| `exportTools` | governance | T3-008, T5-011 |
| `tenancy.*` | governance | T3-008, T5-011 |
| `roles.actors` | governance | T3-002, T3-007, T3-009 |
| `roles.orchestrators` | governance | T3-011 |
| `roles.adminTools` | governance | T5-016 |
| `roles.adminRoles` | governance | T5-016, NT-022 |
| `compensations` | governance | T1-008, T1-012, T1-020, T2-008, T6-004, T6-012 |
| `freshness` | governance | T2-010 |
| `breakGlass.*` | governance | T3-012 |
| `auditTools` | governance | T6-013 |
| `escalation` | governance | T1-021 |
| `policyCheckTools` | governance | T5-014 |
| `capabilities.*` | governance | T2-004, T2-012, T3-001, T3-005, T3-013, T6-007, T6-009, X-005 |
| `languages` | governance | X-014 |
| `slo.successRate` | governance | T1-003 |
| `postconditions` | governance | T1-001, T1-002, T1-003, T1-018 |
| `consistency_required` | AgentCard skill (introduced by NT batch 5) | NT-042 |
| `privacy.disallowedRegions` | governance (introduced by NT batch 4) | NT-021 |
| `readOnlyHint` | MCP tool annotation | T1-002, T1-004, T1-006, T1-007, T1-008, T1-009, T1-011, T1-012, T1-013, T1-014, T1-015, T1-016, T1-017, T1-018 … (72 checks) |
| `destructiveHint` | MCP tool annotation | T1-016, T2-002, T2-004, T2-012, T3-001, T3-004, T3-005, T3-013, T4-004, T4-008, T4-015, T4-018, T6-004, T6-005 … (16 checks) |
| `idempotentHint` | MCP tool annotation | T1-006, T1-011, T2-003 |
| `openWorldHint` | MCP tool annotation | T5-005, T5-017 |
| `inputSchema` | MCP tool descriptor | T1-010, T5-003, T5-007 |

## Written but not read by checks

agentest's importers write these for reports and debugging. No check reads them.

| Attribute | Where | Purpose |
|:--|:--|:--|
| `gen_ai.agent.id` | root span | agent id (the service name) |
| `gen_ai.tool.type` | tool span | `function` |
| `gen_ai.framework` | resource | framework of the native log |
| `service.name` | resource | service name |
| `gen_ai.evaluation.name`, `gen_ai.evaluation.explanation` | event `gen_ai.evaluation.result` | name and note of the verdict |
| `agentest.source.seq` | tool span | original order in the native log |
| `agentest.derived` | tool span (set while reading) | the call was rebuilt from message parts, not from a tool span |
| `agentest.input.family`, `agentest.input.relation` | root span | read only by the opt-in addition T7-017 |

## Decisions (D1–D9)

Approved 18 Nov 2026.

| | Decision |
|:--|:--|
| D1 | OpenTelemetry names first. Where a registry or GenAI name exists it is the canonical name; an `agentest.*` name with the same meaning is a read alias (for example `user.roles`, with `agentest.auth.role` read as an alias). |
| D2 | One canonical name per meaning, older names kept as read aliases: `agentest.output.structured` (alias `agentest.output`), `agentest.task.initial_state` (alias `agentest.undo.before`), `agentest.approval.data_class` (alias `agentest.approval.dataClass`). `agentest.outputs` (a list of observed values) and `agentest.tool.reason` (free text) keep their own meanings. **New cases are new values on existing names, not new names** (for example a new `agentest.approval.kind` value). |
| D3 | Three tiers of declarations: agent-wide policy in the governance extension; per-run declarations on the root span (`agentest.task.*`); set-level declarations (groups, thresholds, load, comparisons) in a run-set manifest, with a fault plan beside it (format 1.1). The tiers do not overlap; where a check reads both governance and a task declaration, it uses both (see the batch pages). |
| D4 | OTLP string arrays for lists of scalars, JSON strings for objects, grouping keys as flat attributes; the reader accepts every form (see [Encoding](#encoding)). |
| D5 | `agentest.trace_format.version` (semver) on the resource or root span, starting at 1.0.0; missing is read as 1.0.0. Phase 2 attributes are 1.1; the run-set manifest and fault plan carry the same version. The semantic-convention version stays on `schemaUrl`. |
| D6 | The schema sets required and required-if; everything else is optional (missing → n/a). Per-check needs are generated from this inventory into [`trace-format-needs.json`](trace-format-needs.json), with set-level needs (a run set, a fault plan) for Phase 2 checks, for use in n/a reasons. |
| D7 | Some facts can be declared per tool (MCP `tools.json`, `_meta` key `agentest/<attribute>`) and per span; the span value overrides the tool value. Those attributes are marked `declarableOn` in the schema. |
| D8 | A record (approval, decision, notice, access log, user setting, DSAR, consent, snapshot, state change, alert) may be a span, a span event or an OTLP log record (`eventName`) with the same attribute names. |
| D9 | Run identity: a run is one trace unless `agentest.run.id` (or OTel span links) joins several traces. Session: `gen_ai.conversation.id` (alias `session.id`). Subject across sessions: `user.id`. Imported runs keep their replay clock; their native start time goes in `agentest.source.start_time_unix_nano`. |

### What the reader does today

The decisions set the format; the reader follows in later, separate changes, each one proven not to move a verdict:

- Aliases read: `session.id` and the older GenAI names (`semconv.yaml`); `agentest.approval.dataClass` as
  `agentest.approval.data_class`, `agentest.output` as `agentest.output.structured`, `enduser.roles` and
  `agentest.auth.role` as `user.roles`, `agentest.undo.before` as `agentest.task.initial_state` (`otel.READ_ALIASES`).
  The canonical name wins when both are present. Alias copies do not count twice in size-based checks.
- `tools.json` `_meta` declarations (D7): `agentest/<attribute>` for the attributes marked `declarableOn: tool`
  (`Agent.declared`); they are applied to each tool span when checks run, and the span's own value wins.
- Record forms (D8): a record may be a dedicated span, a span event or an OTLP log record (`eventName` or the
  `event.name` attribute, with the trace and span ids). `otel.lift_records` turns span records into child spans of the
  span they happened on and event records into root-span events; log records in the same OTLP/JSON file are merged by
  trace id. Not read yet: log records over `agentest std serve` and in OTLP/protobuf files.
- Not read yet: the run-level attributes of D5 and D9 (no check uses them yet), and n/a reasons built from the
  per-check needs (D6).
- `tests/test_reader_verdicts_unchanged.py` proves each reader change keeps every bundled agent's verdicts.

## Planned for 1.1 (Phase 2)

Phase 2 checks judge a set of runs. These names are planned and are not in the 1.0.0 schema:

| Group | Names |
|:--|:--|
| Records | `agentest.environment.change` (`.kind`, `.ref`) |
| Persona and variants (flat keys) | `agentest.persona.<attribute>`, `agentest.persona.variant_of`, `agentest.input.variant_of`, `agentest.input.channel`, `agentest.input.sanitized` |
| Determinism and replay | `gen_ai.response.model`, `gen_ai.request.temperature` (the other replay names are in the NT batch 5 table) |
| Web, network and sandbox (OTel registry) | `http.response.status_code`, `service.version` |
| Task declarations | `agentest.task.safe_states`, `agentest.task.rto_s`, `agentest.task.expect_handoff`, `agentest.task.revocation_window_s` |
| New values on existing names | `agentest.approval.kind=intervention`, `agentest.access.outcome=throttled`, `agentest.ui.action=navigate`/`download`, new `agentest.input.families` values |
| Beside the trace | run-set manifest (which runs belong together, groups, load, thresholds, comparisons), fault plan (what, where, when), governance `sandbox.*`, per-tool `third_party` |

## Validation

`tests/test_trace_format.py` checks that:

- the bundled example traces match the schema;
- records are accepted as spans, span events and log records;
- every `agentest.*` and `gen_ai.*` name the main check code reads is in the schema;
- this page lists every attribute in the schema;
- `trace-format-needs.json` names only schema attributes and covers every check.

```bash
python -m pytest tests/test_trace_format.py -q
```
