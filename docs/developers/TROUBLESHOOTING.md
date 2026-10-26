# Troubleshooting and FAQ

**Almost everything is n/a.** n/a means "no standard signal". Typical causes: no message content in the traces
(content capture is opt-in in OTel GenAI), no `tools.json` (no annotations, no schemas), no injection or
metamorphic inputs in `inputs.json`, or no governance facts. Run `agentest std gen` and record those inputs.

**A read-only tool is reported as a write.** Add it to `tools.json` with `"annotations": {"readOnlyHint": true}`.
MCP's default for an undeclared tool is "may write", and agentest follows it.

**My traces load but no tool calls appear.** Check that tool spans have `gen_ai.operation.name=execute_tool` and
`gen_ai.tool.name`. If your instrumentation uses another convention, rename in the Collector
([INSTRUMENTING.md](INSTRUMENTING.md#collector-configuration-any-vendor-neutral-collector)).

**All runs collapse into one.** Runs are grouped by `traceId`; give each run its own trace. Input ids come from
`agentest.input.id`, then `gen_ai.conversation.id`, then the trace id.

**A text-based check fired on a harmless sentence.** Some checks are English regular expressions. See
[triaging false positives](../testers/FALSE-POSITIVES.md); disable the ID in the config if needed and report it.

**strict and examples disagree.** `examples` also applies `postconditions.byExample` from the AgentCard. A fail only
in examples means the published criteria were not met; check the criteria and the run.

**Does agentest call a model or the network?** No. It reads files and runs deterministic code.

**Do I need agentest in my agent?** No. Agents emit standard traces; agentest is only the judge.

**Which Python?** 3.11 or newer; the only runtime dependency is PyYAML.

**How do I add my own check?** [ADDING-RULES.md](ADDING-RULES.md).
