# Red-team trace pack

Twenty OpenTelemetry GenAI trace files of one made-up support desk agent: nine prompt-injection runs, seven data-exfiltration runs and four over-refusal runs.
Each file holds two runs, `canon` (an ordinary refund request) and one adversarial run. No model, network or key is involved.

- `build.py` writes every file here, plus `docs/guides/RED-TEAM-TRACE-PACK.md`. Edit the specs in it, run it, commit the output. `--check` fails when a committed file is stale.
- `manifest.json` lists each fixture, the verdicts the existing checks give today, and the OWASP Agentic Top 10 entries those checks map to in `taxonomy/asi-mapping.yaml`.
- `agent-card.json` and `tools.json` are the policy the checks read: allowed recipients, allowed hosts, restricted data kinds, and each tool's read-only, destructive and open-world hints.
- `tests/test_redteam_pack.py` asserts the verdicts in CI.

The four over-refusal fixtures are pending: no check in the catalogue judges over-refusal yet, so they carry no expected verdict. When that check lands, add its id and verdicts to each of them.

Guide: [Red-team your agent traces in CI](../../../docs/guides/RED-TEAM-YOUR-AGENT-TRACES-IN-CI.md). Table of fixtures: [Red-team trace pack](../../../docs/guides/RED-TEAM-TRACE-PACK.md).
