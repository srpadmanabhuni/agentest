# Golden cases v2: one pass and one fail case per assessable core test

`golden/golden-cases-v2.jsonl` holds 76 hand-written, synthetic golden cases: a **pass** case and a **fail** case for
each of 38 core tests (coverage 38/38).

Each case is a complete agentest input for one tiny made-up refund desk: an A2A AgentCard with the governance
extension, an MCP `tools.json` and OTLP/JSON traces, plus the verdict a correct check must give for **one** test ID.
The pass case and its fail case differ only in the evidence that test is about (for example the refund amount after
a turn-1 cap, or whether the reply claims a refund that failed). Nothing is a recording of a real agent; all names,
ids, amounts and addresses are invented.

## What is checked here

`tests/test_golden_v2.py` checks the structure of the data only, and imports nothing from the checks themselves:

- each of the 38 test IDs has exactly one `pass` and one `fail` case, and `case_id` values are unique;
- every case is marked `synthetic` with a provenance, and carries an AgentCard, an MCP tool list and OTLP/JSON trace documents;
- every `test_id` is in the vendored catalogue;
- the CSV twin carries the same records as the JSONL, in the same order;
- no case reuses the name of an agent under `agents/`, so none of the locked agent traces, labels or specs is copied or altered.

```shell
PYTHONPATH=src python -m pytest -q tests/test_golden_v2.py
```

Re-deriving each expected verdict with the checks is not part of this change. It needs the check and judge code that
lives on the detector work line, so it will land with that line rather than here.

## Judge questions

Some checks ask a scoring guide a question (is this reply a refusal? which completed action does it claim?). For those
cases the answers are written by hand with the case and stored in `judge_answers` (`guide`, `payload`, `answer`). They
are hand labels for these synthetic cases only; they are not used for, and do not change, any precision or recall
measurement.

## Record fields

| field | meaning |
|---|---|
| `case_id` | `GC2-<test id>-<pass/fail>` |
| `test_id`, `expected_verdict` | the test the case is about and the verdict a correct check gives |
| `reason` | one line: what the case shows |
| `agent_card`, `tools`, `traces` | the agent input (AgentCard, MCP tool list, OTLP/JSON trace documents) |
| `judge_answers` | hand-written answers to the scoring-guide questions the check asks (may be empty) |
| `synthetic`, `label_provenance` | always `true` and `id_specific_trace_case` |

`golden/golden-cases-v2.csv` carries the same records, one row per case, with the agent input in `record_json`.

## What the cases are not

They are test data for the checks, not a benchmark of any agent, and they report no scores. They are not part of any
held-out set and no locked label or data file is changed by adding them.
