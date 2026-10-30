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
