# Glossary

| Term | Meaning |
|---|---|
| **AgentCard** | A2A's JSON description of an agent: name, skills, examples, capabilities, extensions |
| **adapter / dialect** | code that turns a recorded log format into the common trace; per framework, never per agent |
| **canary** | a unique marker planted in untrusted content; its appearance in an action proves an injection was obeyed |
| **catalogue ID** | one of the 130 test IDs (T1-001..T7-014, X-001..X-020) |
| **conformance scenario** | a test-owned oracle in `scenarios.yaml` for agentest's own fixture world of one ID |
| **examples mode** | rules plus the owner's published `postconditions.byExample` |
| **governance extension** | optional AgentCard extension with facts no standard carries (approvals, limits, data classes) |
| **heuristic check** | a check that reads natural-language text with regular expressions |
| **input family** | the kind of test input (canonical, injection, paraphrase, social, ...) |
| **MCP annotations** | `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint` on tools |
| **metamorphic relation** | a change to an input that must not change (or must change in a known way) the outcome |
| **n/a** | no standard signal; not a pass |
| **OTLP/JSON** | the JSON encoding of OpenTelemetry's trace protocol |
| **run** | one trace: one input, one repetition |
| **strict mode** | rules plus harness `gen_ai.evaluation.result` events only |
| **v2 baseline** | the v2 engine's verdicts used to measure v3's defect catch |
| **write** | a tool call that may change state (MCP `readOnlyHint` false or undeclared) |
