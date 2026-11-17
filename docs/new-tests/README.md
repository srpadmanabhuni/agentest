# New tests (Phase 1)

New tests NT-001 to NT-030 add trace checks that close more of the article tests in
[Testing Agentic AI](https://www.linkedin.com/pulse/testing-agentic-ai-dr-srinivas-padmanabhuni-5stoc/).
They read recorded OpenTelemetry traces only, work for any agent and framework, and are opt-in:
the default 130 checks and their verdicts do not change.

- List them: `agentest list --new-tests`
- Run them: `agentest std run --ids NT` (all New tests) or `--ids NT-001,NT-005`
- A check whose trace attributes are missing reports `n/a`, never `pass`.

Each batch documents its checks in its own page (`b1.md` .. `b4.md`) with the trace attributes each check reads.
Every check ships with pass, fail and n/a unit tests built from use case traces.

Enhance and contribute: new checks follow the same layout (one module, one catalogue fragment, one test file, one page).
