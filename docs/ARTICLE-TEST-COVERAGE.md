# Article-test coverage

This page maps agentest checks to **The original 110 tests** in
[Testing Agentic AI](https://www.linkedin.com/pulse/testing-agentic-ai-dr-srinivas-padmanabhuni-5stoc/).
The article tests are numbered A001–A110 in article order. The mapping is a judgement
from each article test's objective and acceptance text. It is test coverage, not a
certification or a compliance determination.

**Counts.** 37 of the 110 article tests are fully covered: the 7 already covered by the
default T1–T7 checks, plus 30 closed by the New tests (`NT-001` to `NT-030`) together with
T1-020 and T1-021. The remaining 73 are unchanged by those checks. Existing default checks and their verdicts do not change.

The New-test closures are the New tests (`NT-001` to `NT-030`) together with the
existing opt-in designs T1-020 (undo; closes A023) and T1-021 (refusal explanation;
closes A031 with NT-016). A002 is closed by two New tests (NT-001 and NT-002). The New
tests and T1-020 / T1-021 stay opt-in: they are not in the default run.

```bash
agentest list --new-tests
agentest std run --agent <dir> --ids NT
```

`agentest std run --ids NT` selects every New test and also T1-020 and T1-021. Missing
trace attributes still give `n/a`, never `pass`.

## Already covered (7)

| Article test | Title | Checks |
|:--|:--|:--|
| A001 | Task Success Rate | T1-001, T1-003, T1-005 |
| A011 | API Action Invocation | T5-001, T5-016, T5-018, T3-002 |
| A015 | Orchestration — Dependency Ordering | T2-001, T2-002, T2-006, T2-009, T2-013 |
| A044 | Security — Unauthorized API Invocation | T4-004, T4-001, T5-001, T5-016, T5-018 |
| A087 | Compliance — Human Oversight Requirements | T2-004, T2-012, T3-004, T3-005 |
| A096 | Access Control Policy Enforcement | T3-002, T3-006, T3-007, T3-008, T3-013, T5-011, T5-016 |
| A101 | Prompt Injection and Instruction Override Robustness | T4-001–T4-018 |

## New-test closures (30)

| Article test | Title | Checks that close it |
|:--|:--|:--|
| A002 | Execution Efficiency | NT-001, NT-002, NT-044 |
| A003 | Autonomous Step Ratio | NT-003 |
| A004 | Tool Selection Accuracy | NT-004 |
| A006 | Task Adherence to Goals | NT-005 |
| A007 | Web Navigation — Page Extraction | NT-006 |
| A008 | Web Navigation — Target Clicking | NT-007 |
| A009 | Web Interaction — Form Filling | NT-008 |
| A010 | API Data Retrieval | NT-009 |
| A012 | Orchestration — Information Flow Integrity | NT-010 |
| A013 | Orchestration — Control Handovers | NT-011 |
| A014 | Orchestration — Subgoal Messaging | NT-012 |
| A017 | Autonomy Trigger — Environment Change | NT-033 |
| A018 | Autonomy Trigger — Limits Exceeded | NT-013 |
| A019 | Autonomy Trigger — Time-Based Relinquish | NT-014 |
| A020 | Autonomy Negative Test — No Unnecessary Handoffs | NT-034 |
| A023 | Feedback Loop for Undo/Remediation | T1-020 |
| A029 | Explainability — Chain-of-Thought Trace | NT-015 |
| A031 | Explainability — Interactive Probing | NT-016, T1-021 |
| A033 | Explainability — Knowledge Graph Integration | NT-017 |
| A034 | Explainability — Financial Decisioning Auditability | NT-018 |
| A035 | Explainability — Adverse Action Generation | NT-019 |
| A053 | Minimization — Sandboxed Deployment | NT-037 |
| A056 | Privacy — PII Handling | NT-020 |
| A059 | DPDP — Cross-Border Transfer Controls | NT-021 |
| A080 | Deployment — Sensitive Data Access Restriction | NT-022 |
| A081 | Deployment — Privacy Violation Monitoring | NT-038 |
| A082 | User Transparency — Inform Users of AI Interaction | NT-023 |
| A083 | User Transparency — Data Control Options | NT-024 |
| A084 | User Empowerment — DSAR Mechanisms | NT-025 |
| A086 | Compliance — Labeling of AI-Generated Content | NT-026 |
| A088 | Financial Use Case — Trading API Authorization Safety | NT-027 |
| A089 | Financial Use Case — Adverse Action Compliance | NT-028 |
| A105 | Reproducible Decision Traces for Auditors | NT-029 |
| A107 | Consent Revocation End-to-End Test | NT-030 |

Three of these checks can only approximate their article tests from what a recorded
trace contains, so they are marked as partial approximations even though they are
counted in the 30 closures:

- **NT-005** (A006): the check covers state-changing calls against the declared action
  set; it does not judge whether a final answer maps to the goal.
- **NT-016** (A031): explanation quality is approximated by citing the target decision's
  recorded inputs or rule, plus a latency bound.
- **NT-029** (A105): “reviewers can reconstruct” is approximated by value lineage to
  recorded sources.

## New tests by ID

| New test | Title | Article test |
|:--|:--|:--|
| NT-001 | Per-task latency within the declared budget | A002 |
| NT-002 | Per-task token and compute cost within the declared budget | A002 |
| NT-003 | Autonomous step ratio meets the declared autonomy level | A003 |
| NT-004 | Expected tool chosen at each step | A004 |
| NT-005 | Actions stay relevant to the stated goal | A006 |
| NT-006 | Extracted page values match the page snapshot | A007 |
| NT-007 | Click lands on the intended element | A008 |
| NT-008 | Forms filled correctly, including validation errors and multi-step forms | A009 |
| NT-009 | API responses mapped to the expected schema | A010 |
| NT-010 | Payload unchanged across agent-to-agent hops | A012 |
| NT-011 | Handovers follow the declared protocol | A013 |
| NT-012 | Sub-goals acknowledged within bounded time | A014 |
| NT-013 | Autonomy limit breach causes a handoff | A018 |
| NT-014 | Agent relinquishes control after its autonomous time window | A019 |
| NT-015 | Stepwise rationale recorded for high-impact decisions | A029 |
| NT-016 | Why probes answered with a valid explanation in time | A031 |
| NT-017 | Structured knowledge lookups shape the answer as declared | A033 |
| NT-018 | Consequential decisions carry principal reasons | A034 |
| NT-019 | Generated decision notices match the declared template | A035 |
| NT-020 | Every PII read is logged | A056 |
| NT-021 | Transfers to disallowed jurisdictions are blocked | A059 |
| NT-022 | Non-privileged roles are denied sensitive data reads | A080 |
| NT-023 | Agent discloses it is an AI | A082 |
| NT-024 | User data controls take effect | A083 |
| NT-025 | Access, correction and deletion requests completed within SLA | A084 |
| NT-026 | AI-generated content carries the declared label | A086 |
| NT-027 | Step-up authorisation before high-impact actions | A088 |
| NT-028 | Decision records reconstruct the required explanation | A089 |
| NT-029 | Reviewers can reconstruct sampled decisions from the trace | A105 |
| NT-030 | Revocation removes stored data and training-queue entries | A107 |
| NT-044 | No state-changing tool calls after a declared task deadline | A002 |
| T1-020 | Undo through the declared compensations (existing design) | A023 |
| T1-021 | Refusal explanation and escalation route (existing design) | A031 |

T1-020 and T1-021 keep their existing IDs and stay out of the default run. Their
rule logic is unchanged.
