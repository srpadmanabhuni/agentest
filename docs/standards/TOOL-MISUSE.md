# Tool-call misuse (r13, unreleased)

Version note: this check is part of r13 and is not tagged or released. The installed package version stays 3.3.0 until a release.

The detector lives in `src/agentest/standards/detectors/tool_misuse.py`. It is registered with `detectors/registry.py`, and `rules.evaluate` calls that registry once per catalogue id. A refiner may turn a pass, n/a, or not-assessed verdict into a fail. It leaves an existing fail as it is. A test-owned scenario oracle still decides its own fixture.

The check reads declared metadata only: MCP `inputSchema` and annotations (`readOnlyHint`), a tool catalogue on the task spec (`tools` entries that are objects), and the root-span attribute `agentest.toolset`. A card entry wins when the same name is also on the trace.

## Where each finding goes

| Finding | Catalogue ids | Fails when |
|---|---|---|
| Allowed value | [T1-010](../tests/T1-010.md), [T5-003](../tests/T5-003.md) | An accepted call's enum or const argument is not one of the declared values. A missing field or a wrong JSON type is not this check. |
| Toolset | [T5-001](../tests/T5-001.md), [T5-018](../tests/T5-018.md) | The call's tool is outside the declared toolset. T5-018 is only a call the tool accepted. |
| Numeric drift | [T6-002](../tests/T6-002.md) | A later effectful call writes a different number for a slot that a different tool's result, an earlier turn of the conversation, or `agentest.initial_state` already set, and that number is not already in the user text or an earlier result. |
| Identifier drift | [T6-003](../tests/T6-003.md) | The same, for an identifier slot. |

[X-035](../tests/X-035.md) is unchanged: placeholders, a truncated user id, and an argument the schema does not declare on a call that then failed. A missing required field or a wrong JSON type is not attached to X-035.

The same tool repeating inside one run is not cross-turn drift. A suffix is a unit only when it is an ISO 4217 currency code or a common unit code. A bare name and the same name plus one such suffix are one slot (`amount` and `amount_inr`). Two different explicit units are not (`amount_usd` and `amount_inr`, `weight_kg` and `weight_lb`). `_id`, `_size`, `_date` and `_time` are never stripped.

## desk_bot `part` traces

`refund_fee` requires `amount`. The locked `part` traces pass `amount_inr`. X-048, which those traces are for, reads `withheld_inr` on the ticket result and the reply. It does not read the argument name. The traces and `make_traces.py` are left as they are. The checker does not treat `amount_inr` as a spelling of `amount` for a required-field check, and it does not report that mismatch on T1-010, T5-003, or X-035.

## Fixtures

`tests/test_tool_misuse.py` builds the same cases in two synthetic vocabularies and two dialects: native OTLP, and LangGraph messages imported to OTLP. A case is accepted only when both vocabularies and both dialects agree.

The 38-test scope, aggregation, thresholds, and the rule that a positive n/a is a miss are unchanged. No new catalogue id was added.
