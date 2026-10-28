# Reading results

Every agent gets a verdict for each of the 136 catalogue IDs:

| Verdict | Meaning | What to do |
|---|---|---|
| **pass** | the needed signal was in the evidence and the property held | nothing; a pass is only as good as the inputs that were run |
| **fail** | the property was violated; `detail` names the run (`input_id#rep`) and the evidence | triage (below), then file a [defect report](DEFECT-REPORTS.md) or a [false-positive report](FALSE-POSITIVES.md) |
| **n/a** | no standard signal: no input of the needed kind, or a needed fact is not declared | decide whether the risk applies; if it does, add the input or the fact and re-run |

n/a is never counted as a pass. A report with many n/a verdicts has low coverage, not high quality.

## The two modes

| | `--mode strict` | `--mode examples` (default) |
|---|---|---|
| universal rules over OTel + AgentCard + MCP | yes | yes |
| harness `gen_ai.evaluation.result` events | yes | yes |
| `postconditions.byExample` from the AgentCard | no | yes |
| trusts criteria written by the agent's owner | no | yes |

Use strict for independent assessment, examples when the owner's published success criteria are agreed.
On the bundled 85 agents (15 samples plus a01–a70), the v2 defects caught are 391/394 (examples) and 385/394
(strict); see [REGRESSION.md](../standards/REGRESSION.md).

## Reading a detail string

`case2#0: reply denies executed ['ai-133']` means: input `case2`, repetition 0; the reply says the object `AI-133`
was not done, but the trace shows the state-changing call succeeded and an effect executed.

## Formats

- terminal summary: one line per agent with the failing IDs;
- `--format md|html`: tables for humans;
- `--format junit`: fail = failure, n/a = skipped (CI dashboards);
- `--format sarif`: code-scanning viewers;
- `--format json`: versioned `agentest.verdicts/1` for tools.
