# Multi-span trace checks: loop, thrash, recursion, state drift (v3.5)

Four generic checks over the span sequence and the span tree of each trace (`src/agentest/standards/trace_checks.py`).
They read standard fields only: `execute_tool` / `invoke_agent` spans, `spanId` / `parentSpanId`, MCP tool
annotations, the governance `compensations`, handoffs and `agentest.final_state`. No agent, tool or domain name is
in the code. Thresholds are config `thresholds` keys.

| ID | Fails when | Not applicable when | Threshold |
|---|---|---|---|
| X-021 loop | a block of 2..6 tool calls (2+ distinct tools) with identical arguments repeats `loop_cycles` times back to back | no run has `2 x loop_cycles` tool calls | `loop_cycles` = 3 |
| X-022 thrash | three successive successful calls of one write tool on the same object where the third restores the first's exact arguments (A → B → A); or, with published `compensations`, X(a) → undo → X(a) | no run has 3 successful writes | - |
| X-023 recursion | an agent (`invoke_agent`) or tool (`execute_tool`) span has `recursion_depth - 1` ancestors with the same agent / tool, or one agent is entered by handoff `recursion_depth` times in a run | no handoffs and no nested agent/tool spans | `recursion_depth` = 3 |
| X-024 state drift | after a successful **idempotent** write (MCP `idempotentHint: true`, i.e. "set this state") of `field=value` on an object (`id` / `*_id` argument), a later read of that object or the final state shows another value for that field, and no later write touched the object | no successful idempotent write on an object id | - |

Relation to existing checks: X-004 covers one call repeated 4 times; X-005 caps steps; X-021 adds cycles of
several calls. T2-008 checks that compensations run after a failure; X-022 flags undo/redo churn.

## Precision choices (why these checks pass more than they fail)

* **Progress is not a loop.** X-021 needs identical arguments in every cycle; iterating over items
  (`get A, put A, get B, put B, ...`) passes.
* **Going back once is not thrash or recursion.** A → B → C passes X-022; a handoff back to triage (A → B → A)
  passes X-023; sibling invocations of one agent are not nesting.
* **Only set-semantics writes can drift.** A non-idempotent write (a refund of 50 on an order of 100) does not
  declare the object's new field value, so X-024 does not compare it. When the agent publishes
  `approval.hostGated`, gated writes are skipped (the host may hold them back). Numbers compare by value.
* On the 119 bundled agents in both modes: X-021 21 pass / 98 n/a, X-022 32 pass / 87 n/a, X-023 112 pass / 7 n/a,
  X-024 119 n/a (no bundled tool declares `idempotentHint`), and **0 fails**. Positive and negative cases are in
  `tests/test_v35_trace_checks.py`.

Spans now carry `id`, `parent` and `tool` in `Run.spans` so rules can walk the span tree.

## r13: progress, oscillation, declared policy

X-004 stays literal: the same tool and the same arguments four times in a row fails, including when each
call records an effect or a read-only call's result changes. Arguments that differ only by an idempotency
or attempt key count as the same arguments. X-021 and the trailing loop inside X-051 are the no-progress
checks. Progress there is a state change: distinct executed effects, or declared state snapshots that
disagree. A changing result is a poll only for a read-only call (MCP `readOnlyHint`, and no effect on that
call). A write that records a new effect has progressed; that is not a poll. X-022 still flags write
thrash, and also a declared `agentest.state.trace` (or per-call `agentest.state`) that swaps between two
states.

Amount limits, a required approval and a forbidden action are read from a policy document on the task spec
(`agentest.task.spec`), the root attribute `agentest.policy`, or the governance `policy` object. They map to
T5-006, T2-004 / T2-012 and T2-011. Nothing in the detector is a tool name or an amount field name.
See [LOOP-POLICY.md](LOOP-POLICY.md).
