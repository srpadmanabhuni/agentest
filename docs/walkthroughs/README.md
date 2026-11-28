# Walkthroughs: bring an agent trace, contribute a test

Eight worked examples. Each walkthrough starts from a recorded example trace in this repo, runs agentest on it, and explains the verdicts.
They need just the base install (`pyyaml`); no model and no access to the agent.

| # | Walkthrough | Checks |
|---|---|---|
| 1 | [The agent acts before it verifies the patient](01-verify-before-acting.md) | T2-001, T2-005. Also the synthetic pair: failing trace, evidence, fixed trace, rerun |
| 2 | [Instructions hidden in tool output](02-instructions-hidden-in-tool-output.md) | T4-001, T4-002, T4-003, T4-012 |
| 3 | [Your agent says done. What does the trace prove?](03-claims-success-it-did-not-earn.md) | T1-002, T1-018, T3-006 |
| 4 | [Personal data left unmasked](04-personal-data-left-unmasked.md) | T7-014 |
| 5 | [Bring your own log](05-bring-your-own-log.md) | any |
| 8 | [Post a redacted agent report](08-post-your-report.md) | T5-007 |
| 9 | [Read the trace when a check fails](09-read-the-trace.md) | T1-018 |
| 10 | [Compare two saved runs with std diff](10-compare-two-runs.md) | T1-018, T2-001, T4-003, T7-014 |

Commands run from the repository root after `pip install -e .`.
