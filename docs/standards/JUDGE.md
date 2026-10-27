# The judge: semantic questions, scoring guides, not-assessed (v3.4)

Since v3.4, no regular expression decides a verdict on natural language. Each check uses three mechanisms, in this order:

1. **Structural trace checks.** These are exact and language-independent. They cover tool calls, arguments, results,
   span timing, `gen_ai.usage`, approval decisions and handoffs. Examples: an id or amount in the answer must be grounded
   in a tool result of the same run, and an approval decision must sit on the span of the agent that executes the call.
2. **Format validators.** These parse machine formats (ids, emails, URLs, digests, JSON fields). They are listed in
   `FORMAT_VALIDATORS` in `rules.py`. `PREFILTERS` only narrow which spans are examined.
   `scripts/regex_final_count.py` counts the patterns that are neither. CI requires that count to be 0.
3. **The judge.** It answers questions of meaning: does this reply refuse, claim an action, give a reason, or switch
   language? Do two replies differ in tone? It works in any language or script.

## Interface

The judge is any OpenAI-compatible `/chat/completions` endpoint. It is called with the Python standard library, so
there is no SDK and no vendor lock-in. The documented default is a local llama.cpp server running Qwen2.5-7B-Instruct
(GGUF Q4_K_M), which costs nothing and needs no key.

| setting | flag | environment |
|:--|:--|:--|
| endpoint (`local` = `http://127.0.0.1:8080/v1`, `off` = none) | `--judge` | `AGENTEST_JUDGE_URL` |
| model name (sent and recorded) | `--judge-model` | `AGENTEST_JUDGE_MODEL` |
| bearer token (never written anywhere) | — | `AGENTEST_JUDGE_KEY` |
| answer cache (JSON lines) | `--judge-cache` | `AGENTEST_JUDGE_CACHE` |
| replay only: never call the endpoint | `--judge-offline` | `AGENTEST_JUDGE_OFFLINE=1` |
| parallel requests | — | `AGENTEST_JUDGE_WORKERS` (default 1) |

Every call is made the same way:
- One scoring guide per request.
- `temperature` 0, fixed `seed` 42, and a JSON-only answer.
- The answer is validated against the guide's output schema. An invalid answer counts as no answer.

Answers are cached by `sha256(model | guide id | guide version | prompt version | payload)`. The repository ships the
answers for its bundled agents in `fixtures/judge/*.jsonl`. With those, `--judge-offline` reproduces the judge-on
verdicts with no model and no network, which is how CI runs.

Every result that used the judge records the judge identity (model, endpoint, temperature, seed, prompt version) at
the top of the JSON report. Per verdict, it records the guide ids and versions it asked
(`verdicts.schema.json`, field `judge`).

## Without a judge: `not-assessed`

A check whose verdict needs a semantic answer reports `not-assessed` when no judge is configured, or when an offline
replay has no cached answer. This status is neither a pass nor a fail. agentest never silently falls back to keywords
or regular expressions. The structural part of such a check still runs: a structural fail stays a fail.

## Scoring guides

The scoring guides are open, one YAML file per question in
[`src/agentest/standards/guides/`](../../src/agentest/standards/guides/). Each file has these fields:

```yaml
id: refusal
version: 1                 # bump on any change of meaning; cached answers of older versions are not reused
checks: [X-015, T7-001]    # IDs that ask it (documentation)
payload: "text: one message; role: who wrote it"
question: |
  Is the text a refusal ...?
rubric: |
  - Any language or script. Judge meaning, not keywords.
output:                    # JSON Schema of the answer
  type: object
  properties: {refuses: {type: boolean}}
  required: [refuses]
```

## Calibration

The bundled judge is not calibrated: it is a local 7B model with open guides, and its answers can be wrong.
Because the endpoint is pluggable, any model can replace it. A calibrated judge is available separately as a paid
offering. It consists of a model and its settings, checked against labelled data with published agreement figures.
Its calibration labels, datasets and results are not part of this repository, and nothing in this repository
depends on them.
