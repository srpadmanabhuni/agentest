# Golden cases v2: one pass and one fail case per assessable core test

`golden/golden-cases-v2.jsonl` holds 76 hand-written, synthetic golden cases: a **pass** case and a **fail** case for
each of the 38 assessable core tests listed in `fixtures/core-assessable.json` (coverage 38/38).

Each case is a complete agentest input for one tiny made-up refund desk: an A2A AgentCard with the governance
extension, an MCP `tools.json` and OTLP/JSON traces, plus the verdict a correct check must give for **one** test ID.
The pass case and its fail case differ only in the evidence that test is about (for example the refund amount after
a turn-1 cap, or whether the reply claims a refund that failed). Nothing is a recording of a real agent; all names,
ids, amounts and addresses are invented.

## Re-derive every verdict

```shell
PYTHONPATH=src python golden/check_golden_v2.py          # 76/76 cases agree, or exit 1
PYTHONPATH=src python golden/build_golden_v2.py          # rebuild the JSONL and its CSV twin from the source
PYTHONPATH=src python -m pytest -q tests/test_golden_v2.py
```

`check_golden_v2.py` writes each case to a temporary agent directory, runs the agentest checks on it and compares the
status of the case's own test ID with `expected_verdict`. It needs no network and no model.

## Judge questions

Some checks ask a scoring guide a question (is this reply a refusal? which completed action does it claim?). For those
cases the answers are written by hand with the case and stored in `judge_answers` (`guide`, `payload`, `answer`). The
checker replays only these answers, from a private offline cache; the bundled caches are not used, and a question
without a hand-written answer would leave the check not-assessed rather than guessed. The labels follow the rubric in
`src/agentest/standards/guides/<guide>.yaml`.

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

They are a regression oracle for the checks, not a benchmark of any agent, and they report no scores. The golden v1
records (abstract per-check records, 16 cases) stay as they are; v2 adds full agent inputs.
