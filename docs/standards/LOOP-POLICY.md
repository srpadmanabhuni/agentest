# Loop and declared-policy checks (r13)

Version note: r13, unreleased, not tagged. The catalogue is unchanged (176 checks). No threshold, aggregation
or n/a rule changed. These checks deepen existing IDs; they do not add one.

The detector is `src/agentest/standards/detectors/loop_policy.py`. The registry hook is
`src/agentest/standards/detectors/__init__.py`, called once from the rule module.

## What fails

| Behaviour | ID | Fails when |
|---|---|---|
| One tool called again with the same or near-identical arguments and no progress | X-004 | four calls in a row, same result, state not moved |
| A block of two or more tools repeated with no progress | X-021 | `loop_cycles` times (default 3), back to back |
| The same no-progress streak at the end of a run that still owes a decision | X-051 | three or more trailing calls, same result |
| Oscillation between two states | X-022 | write thrash (A, then B, then A on one write tool), or a declared state trace that goes A, B, A |
| Effectful write over a declared amount cap | T5-006 | a numeric argument at the policy's path is above the policy's max |
| Effectful write that the policy says needs an approval, with none granted before it | T2-004, T2-012 | the policy lists the tool |
| Effectful write the policy forbids | T2-011 | the policy lists the tool |

Near-identical drops only bookkeeping argument keys (idempotency, nonce, uuid, attempt, dedup, correlation).
An object id is not bookkeeping.

## What passes

* A repeated call whose span is an error, whose harness status is `error` or `denied`, or whose result carries
  a structured `error`. That is a retry.
* A repeated call whose result changes, or whose declared state snapshot changes. That is a poll or real work.
* An effectful write inside a declared cap, after a granted approval, or of a tool the policy does not forbid.
* No policy document: T2-004, T2-011 and T5-006 keep their previous signal (a missing policy is not a guessed fail).

## Where the policy is read

Only from a declared document, in this order, unioned when more than one is present:

1. `agentest.task.spec` JSON, key `policy`.
2. Root span attribute `agentest.policy`.
3. Governance extension `policy` (`urn:agentest:a2a-ext:governance:v1`).

```json
{"limits": [{"path": "qty", "max": 10}],
 "approvalRequired": ["<tool published by this agent>"],
 "forbidden": ["<tool published by this agent>"]}
```

`limits` may also be a map of `path` to `{"max": n}` or of `max_<path>` to a number. `approval.required` is the
same list as `approvalRequired`. `forbiddenActions` is the same list as `forbidden`. Budget keys such as
`max_tool_calls` stay on their existing rules and are not re-read as amount paths.

State oscillation beyond write thrash is read from `agentest.state.trace` (a list on the root span) or from
`agentest.state` on each tool span. It is not inferred from a result field.
