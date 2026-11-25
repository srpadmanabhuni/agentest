# Failure Lab 001: can this refund agent retry safely after a timeout?

**Here is the reproducible test.** When the `submit_refund` call in the OpenAI Agents SDK refund example
times out and the agent calls it again, the refund service creates a second refund for the same order.
Sending one idempotency key per refund request turns the retry into a lookup of the refund that already
exists. The run below needs no API key and no network.

This finding is about one example and one version, under the conditions listed below. It is not a statement
about the OpenAI Agents SDK as a whole. The SDK reports the timeout correctly; the duplicate comes from a
refund tool that has no way to recognise a repeated request.

## What was tested

| | |
|---|---|
| Example | [`examples/basic/stream_ws.py`](https://github.com/openai/openai-agents-python/blob/v0.26.0/examples/basic/stream_ws.py) in openai/openai-agents-python |
| Version | tag `v0.26.0` (commit `0ad2d63a9371a23333a95ea6878141a826c9cdda`), `pip install openai-agents==0.26.0` |
| File checked | sha256 `f9071975a51934789c76aa2f5cdfb765404e61f5fbc709423eb5e987f4e16cce`; unchanged on `main` at `4e162c79a4a951c6fc8b698d5c8279c1963c099b` (24 Nov 2026) |
| Agent | `SupportAgent` with `lookup_order`, `refund_policy_specialist` (an agent used as a tool) and `submit_refund` (`needs_approval=True`) |
| Failure | the first `submit_refund` reply is slower than the tool timeout; the refund was already created when the timeout fires |

[`refund_agent.py`](refund_agent.py) keeps the example's agents, instructions, tool names, arguments and
approval setting. It changes four things, so anyone can rerun it:

1. **Scripted model.** `ScriptedModel` makes the model's choices in a fixed order: look up the order, ask the
   policy specialist, submit the refund, and call `submit_refund` again with the same arguments if the last
   result says the call timed out. Whether a live model retries here depends on the model; the script fixes
   that choice so the tool side can be studied. This lab did not run a live model.
2. **A refund service.** `RefundLedger` stands in for a payments API. It creates the refund when the request
   arrives; its first answer then takes 0.6 s.
3. **A tool timeout.** `submit_refund` uses the SDK's per-tool `timeout` option (0.2 s). The SDK supports that
   option on async tools only, so the lab's `submit_refund` is `async`. The example itself sets no timeout.
4. **Approval.** Every approval prompt is approved, as the example does with `EXAMPLES_INTERACTIVE_MODE=auto`.

## Reproduce

From the repository root, on Python 3.11 or newer:

```bash
python3 -m venv .venv
```

```bash
. .venv/bin/activate
```

```bash
pip install -e ".[dev]" openai-agents==0.26.0
```

```bash
python examples/failure-lab/001-refund-timeout-retry/reproduce.py --variant original
```

To judge the recorded traces without installing the SDK:

```bash
agentest std run --otlp examples/failure-lab/001-refund-timeout-retry/traces/original.otlp.json \
    --tools examples/failure-lab/001-refund-timeout-retry/tools.json --ids T2-003,T1-006,T1-011 --format md
```

## Observed behaviour (original tool contract)

```text
variant: original
answer: RF-1002
submit_refund calls: 2
refunds created: 2 ['RF-1001', 'RF-1002']
T2-003 fail repeated side effects: ['refund-ORD-1001#0:effect x2']
T1-006 fail repeated side effects: ['refund-ORD-1001#0:effect x2']
T1-008 pass no half-applied writes
```

1. `submit_refund(ORD-1001, 49.99, "Item arrived damaged")` is approved and sent. The service creates RF-1001.
2. The answer is late. The SDK returns `Tool 'submit_refund' timed out after 0.2 seconds.` to the model.
3. The model calls `submit_refund` again with the same arguments. It is approved again and the service creates RF-1002.
4. The agent replies `RF-1002`. The customer has two refunds for one damaged mouse; the reply names only one of them.

The recorded run is in [`traces/original.run.json`](traces/original.run.json) (the SDK's `to_input_list()`,
the approvals and the refunds the service created) and [`traces/original.otlp.json`](traces/original.otlp.json).

## The agentest checks that catch it

**T2-003** (with T1-006 and T1-011, which share its implementation): a non-idempotent state-changing tool
runs at most once per identical request in a run. The trace records each refund the service created as an
executed effect, and two identical refund effects fail the check. See [T2-003](../../../docs/tests/T2-003.md).

What it does not catch, so you can judge the boundary:

- **Tool calls alone are not enough.** The first call is recorded as an error (it timed out), so a trace with
  only tool calls shows one successful refund call. The duplicate is visible once the trace includes what the
  refund service actually did. Without those effect records, T2-003 passes on the original run.
- **T1-008** (half-applied writes) passes: a failed write that is later retried successfully counts as
  recovered.
- **X-017** (one approval request per action and object) fails on both versions: the reviewer is asked twice
  to approve the same refund, even after the fix. That may be worth its own change in a real deployment.

## Suggested fix: one idempotency key per refund request

```python
def refund_key(order_id: str, amount: float) -> str:
    return "refund-" + hashlib.sha256(f"{order_id}|{amount:.2f}".encode()).hexdigest()[:16]


@tool(needs_approval=True, timeout=TOOL_TIMEOUT_S)
async def submit_refund(order_id: str, amount: float, reason: str) -> dict[str, Any]:
    """Create a refund request. This tool requires approval."""
    return await LEDGER.create(order_id, amount, reason, idempotency_key=refund_key(order_id, amount))
```

The service stores the key with the refund. A retry with the same key returns RF-1001 again
(`"replayed": True`) instead of creating a new refund:

```bash
python examples/failure-lab/001-refund-timeout-retry/reproduce.py --variant fixed
```

```text
variant: fixed
answer: RF-1001
submit_refund calls: 2
refunds created: 1 ['RF-1001']
T2-003 pass no duplicate side effect over 1 run(s)
T1-006 pass no duplicate side effect over 1 run(s)
T1-008 pass no half-applied writes
```

The key above allows one refund per order and amount; a service that allows several partial refunds would
key on the request instead. Another fix is to read the refunds for the order back before retrying.

## Regression test

[`tests/test_failure_lab_001.py`](../../../tests/test_failure_lab_001.py) runs the workflow end to end and
asserts that one refund is created. It passes with the fix. On the original tool contract it is marked as an
expected failure; `--runxfail` runs it as a normal test so you can see it fail:

```bash
python -m pytest -q tests/test_failure_lab_001.py
```

```bash
python -m pytest -q tests/test_failure_lab_001.py --runxfail
```

The first two tests judge the recorded traces and need agentest only. The end-to-end tests skip unless
openai-agents 0.26.0 is installed.

## Reproduce it, challenge it, or fix it

Did you get a different result, with this example, another version, or a live model? Do you think the test is
unfair, or that the fix is wrong? Say so in the [Failure Lab discussion issue](https://github.com/srpadmanabhuni/agentest/issues?q=label%3Afailure-lab)
or open a pull request. Useful reproductions, corrections and fixes are credited in this README and in
[CONTRIBUTORS.md](../../../CONTRIBUTORS.md).

## Files

| File | What it is |
|---|---|
| [`refund_agent.py`](refund_agent.py) | The example's agents and tools, the scripted model and the refund service |
| [`reproduce.py`](reproduce.py) | Runs one variant, writes its traces and prints the verdicts |
| [`to_trace.py`](to_trace.py) | Turns a recorded run into an agentest trace (agentest only) |
| [`tools.json`](tools.json) | The three tools with MCP annotations; `submit_refund` is not idempotent |
| [`traces/`](traces/) | The recorded runs and traces for both variants |
