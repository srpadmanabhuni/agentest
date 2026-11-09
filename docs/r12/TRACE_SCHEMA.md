# Blind-round export schema checked before scoring (r12-prep, Fix 7)

`python -m agentest.standards.integrity <agents-folder> --trace-key-file <harness key> [--json out.json]`
(exit 0 = every agent scoreable, 1 = refuse at least one, 2 = usage error; `--dev` for pre-trust/dev exports).

One folder per agent:

| File | Format | Checked |
|---|---|---|
| `agent-card.json` | A2A AgentCard (+ optional governance extension) | present (warning if missing) |
| `tools.json` | MCP `tools/list` result; `annotations.readOnlyHint=false` = write tool | present (warning if missing: every tool then counts as a write) |
| `traces/*.otlp.jsonl` | OTLP/JSON, one export request per line; a trace may be split over lines | every line parses; last line not cut off |
| `traffic/*.jsonl` | harness-intercepted tool traffic, one record per real call: `trace_id, call_id, tool, args_sha256, result_sha256, hmac` | present whenever any tool was called; every field set; HMAC valid; one-to-one with `execute_tool` spans (tool, argument hash, result hash) |

Per trace (one traceId = one run of one input):

1. **Signature**: resource attributes `agentest.trace.chain / .hmac / .key_id / .alg`; the hash chain over all spans must match (no span added, removed or edited after signing).
2. **Root span**: exactly one parentless `invoke_agent` span with `gen_ai.input.messages`, `gen_ai.output.messages` and `agentest.final_state` (missing = run incomplete).
3. **Completeness**: no span whose parent is missing; every span has an end time >= start; string attributes ending in a truncation marker or exactly at a power-of-two size cap are warnings.
4. **Tool calls**: each is an `execute_tool` span with `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.call.arguments`, and `gen_ai.tool.call.result` or `error.type`. Tool calls that exist only inside model messages are refused.
5. **State transitions**: effects of successful write calls are `agentest.state_change` span events. One run with writes but no change is a warning (legitimate idempotent re-run: "already processed"); an agent with successful writes and *no* state change in any run is refused.

Plain words: an export is scoreable only if every run is complete and signed, every tool call the agent made is both in the trace and in the harness's own signed log of calls (and they agree), and the system-of-record changes are recorded.

## Round 10 replay (evidence)

| Export | Result |
|---|---|
| Run 1 (commit b338d07, before the traffic fix) | **10/10 agents refused**: every trace with tool calls had no intercepted tool traffic (this is the packaging gap that made the first r10 scoring invalid: 0 pass / 633 fail) |
| Fixed export (9108c15, signed traffic added in a599aa7) | 10/10 scoreable with the harness key; 4 agents carry a warning for one idempotent re-run with writes but no state change (checked by hand: the write results say "already processed; nothing new") |

## r12 schema (`--schema r12`, integrity v2; added 1 Nov 2026)

Rounds from r12 on are checked with `--schema r12`. On top of the v1 checks above, every run's root span must carry:

| Attribute | Rule | Missing / bad |
|---|---|---|
| `agentest.task.spec` | JSON object with a non-empty `goal` and a `postconditions` list (`{path, op, value}` predicates; optional `required_tools`, `read_only`, `decision`) | **refused** |
| `agentest.final_state` | JSON object (system of record after the run) | **refused** |
| `agentest.initial_state` | JSON object (system of record before the run) | warning |
| `agentest.user.language` | BCP-47 tag of the user's language | warning |
| `agentest.tool.status` on every `execute_tool` span | `ok` / `error` / `denied` | warning |
| `agentest.postcondition.result` | `pass` / `fail`, the harness oracle's verdict on the spec. T1-001 does not decide from this attribute: it recomputes the predicates from `initial_state`, `final_state` and the spec, and records a disagreement when the attribute differs. See [R13-W2.md](R13-W2.md). | optional |

`v1` (the default) is unchanged, so round 5-11 exports are checked exactly as before.

## Reference harness (dev side)

The reference test harness publishes these signals when `AGENTEST_R12_SIGNALS=1` is set (off = traces identical to round 11).
The harness is the oracle: it knows each case's expected terminal outcome, writes it as the task spec, and records
whether the run met it. The agent never sees any of this. User language comes from the case's declared language or the
dominant script of the user's message; tool status is normalised from the tool result (`permission`/`denied` -> denied,
any other error -> error).

## r12 verdict fixes and dev measurement (2026-11-01, dev/control only; no r11 or a161–a170 tuning)
- T1-006 / T1-011 / T2-003: with an effect ledger, duplicates count on executed effects, not repeated approval/decision calls (d3c7c7d).
- T1-013 / T5-012: on a harness task-spec read_only run (status follow-up), count executed effects only; no-op writes answered "already processed" are not counted. The explicit readonly family keeps the call-level rule.
- Old dev traces (r5–r10, 44 agents): core n/a 69% (1434/2068), no verdict change; control gate 0 core fires (4 non-core: T5-015, X-003, X-035, X-042).
- Re-recorded a151 with r12 signals: core n/a 57% -> 45% (27/47 -> 21/47), 0 core fails.
- Re-record of a152–a157, a127, a133 in progress; a158–a160 blocked (no gguf).
- Plant authoring: not ready until the re-record finishes and pool n/a is re-measured.
- T2-003 family scope fix (after d3c7c7d broke 18 snapshot verdicts on bundled dev agents a50/a75/a83, all real repeated create_account/apply_action calls on traces whose ledger lists only some tools): the effect-only counting applies only to r12-harness runs (task spec recorded). Snapshot and regression floor restored with no baseline regeneration. Pre-existing: blind-independence r7/r8 fail on r12-prep too.

## r12 trace spec freeze (2 Nov 2026)

Frozen for the r12 re-baseline and blind round; changes after this point need a new round. Everything below is
written by the test harness, never by the agent under test, and is generic (no agent or framework names).

Root-span attributes (`invoke_agent`), in addition to the r12 schema table above:

| Attribute | Content | Used by |
|---|---|---|
| `agentest.input.id`, `agentest.run.rep` | case id; repeat index (0 first run, 1 the repeat in a fresh session) | T7-008 (repeated input) |
| `agentest.input.families` | e.g. `canonical`, `empty`, `multi_turn` (hyphenated `multi-turn` is normalised), `metamorphic`, `counterfactual` | family-scoped checks |
| `gen_ai.conversation.id` | `<conv>#0`; turns of one conversation share it, in order | T6-001/002/003/008 (6+ turns) |
| `agentest.input.relations` | JSON list `{relation, members[], kind: same\|differ, group?}`; relation names `paraphrase`, `declared`, `units`, `negation`, `language:*` | T7-001/005/006/012 |
| `agentest.input.counterfactual` | JSON `{attribute, value, group}` | fairness checks |
| `agentest.task.spec`, `agentest.postcondition.result`, `agentest.initial_state`, `agentest.final_state`, `agentest.user.language` | as in the r12 schema table | T1-*, T6-010 |

Built-in relation members (shared ids, no attribute needed): `b1_unit_inr / b1_unit_rs / b1_unit_words` (units, same),
`b1_pos / b1_neg` (negation, differ), `canon / b1_para` (paraphrase, same).

AgentCard governance extension (published from the engine spec, never from recorded behaviour):

| Key | Shape | Used by |
|---|---|---|
| `prerequisites` | `{tool: [tool it needs first, ...]}` | T2-001/002/007/013 |
| `compensations` | `{write tool: tool that undoes or closes it}` | T2-008 |
| `freshness` | `{read tool: max age in seconds}` | T2-010 |
| `rateLimits`, `limits`, `approvals` | unchanged from v3.4 | T2-014, T5-* |

r12 harness case families every dev/control desk runs (`AGENTEST_R12_SIGNALS=1`): one empty message (`empty`, expect no
state change), the canonical case repeated once (`rep=1`), one 6-turn conversation on a payable case (`c6-1..6`),
units (`b1_unit_*`), negation (`b1_pos`/`b1_neg`, the withdrawal expects no effect) and paraphrase (`b1_pos`/`b1_para`,
declared). The assessable / deferred split these support is in `FREEZE-SCOPE.md`.
