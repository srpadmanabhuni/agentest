# New tests

New tests NT-001 to NT-030 and NT-038 to NT-046 add trace checks that close more of the article tests in
[Testing Agentic AI](https://www.linkedin.com/pulse/testing-agentic-ai-dr-srinivas-padmanabhuni-5stoc/).
They read recorded OpenTelemetry traces only, work for any agent and framework, and are opt-in:
existing default checks and their verdicts do not change.

- List them: `agentest list --new-tests`
- Run them: `agentest std run --ids NT` (all New tests, plus T1-020 and T1-021) or `--ids NT-001,NT-005`
- `agentest list --new-tests` lists the New tests and, when present, T1-020 and T1-021. All stay out of the default run.
- A check whose trace attributes are missing reports `n/a`, never `pass`.

Each batch documents its checks in its own page (`b1.md` .. `b4.md`, [b5.md](b5.md) and [b6.md](b6.md)) with the trace attributes each check reads.
Every check ships with pass, fail and n/a unit tests built from use case traces. Checks after NT-030 stay opt-in and are not part of the published test count.

Enhance and contribute: new checks follow the same layout (one module, one catalogue fragment, one test file, one page).
