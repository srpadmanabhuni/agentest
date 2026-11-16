## How agentest relates to the Hugging Face checklist

The [Agentic AI Test Checklist 110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) is the specification, the *what*: each test's objective, acceptance criteria and pass/fail signals. agentest is one execution engine for it, the *how*: a deterministic program that judges recorded agent behaviour against those requirements. The checklist stands on its own for planning, manual testing and governance; agentest makes the checks repeatable.

**What agentest automates**

- One automated check mapped to each of the 110 checklist IDs, plus 20 repo extensions (`X-001` to `X-020`): 130 checks across task success, ordering, authorisation, prompt injection, tool allowlists, state drift and consistency. These automate trace-based checks, not the full manual procedures on the card; what each check can decide depends on the evidence in your traces and artifacts.
- Deterministic `pass` / `fail` / `n/a` verdicts with an evidence line each, read from OpenTelemetry GenAI traces, A2A AgentCards and MCP tool lists. Offline, no LLM judge: the same input always gives the same verdict.
- CI gating: `--strict` fails the build on any `fail`, with JUnit, SARIF, JSON, HTML, CSV and Markdown output.

**What evidence it needs**

A check can only judge what your traces and artifacts record. When the signal a check reads is not there, the verdict is `n/a`, never a silent pass. An `n/a` can mean the agent never emitted the needed signal, or that the check does not apply to your setup; either way it is a pointer to look closer, not a result. Some checks are regex or text-matching heuristics; treat those verdicts as a signal to review, not proof.

**What still needs people or other tools**

- Tests the trace cannot see. Many checklist rows also describe manual procedures and fixture-based challenges, for example probing a live agent with an injection attempt and watching which tools it calls. Those stay human-led, or need a harness that exercises a live agent.
- Judgement calls. Triaging a heuristic `fail`, deciding acceptable risk, and reviewing a vendor's evidence all stay with people.
- Compliance sign-off. The standards mappings are indicative pointers, not a determination, and a green agentest run is not certification.
- Anything outside the 130 checks. Your own risks, implemented in your own harness, can still cite the same published IDs for traceability.

**One ID, one requirement.** The dataset, this runner, the docs and the browser report card all use the same IDs, so every verdict names the published requirement it judged. Comparable results across tools need more than the same ID: the same catalogue version, the same interpretation of the criteria and the same evidence assumptions. Implementations can legitimately differ; a `fail` on T4-003 always points to the same requirement text, whichever engine raised it.
