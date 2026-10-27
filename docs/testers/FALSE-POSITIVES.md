# Triaging false positives

A fail is a claim about evidence. Before filing a defect, check:

1. **Is the evidence right?** Open the trace for the run named in the detail. Are the tool annotations correct
   (`readOnlyHint`)? Is the governance fact (approval list, limits) what the owner intends?
2. **Is it a heuristic check?** IDs marked *heuristic: text patterns* in the [per-test guide](PER-TEST-GUIDE.md)
   read English text with regular expressions (claims of success, refusals, warnings, directives). Paraphrases,
   other languages and quoted text can fool them.
3. **Is it a threshold?** Budget checks (X-005..X-007, T5-006) depend on limits. Agree the limit and set it in the
   AgentCard `limits` or the config `thresholds`.
4. **Is it the input?** A canary that is an ordinary word, or an injected directive that is also the user's own
   request, produces misleading verdicts. Fix the `agentest.input.families` label on the run's root span.

## Temporary suppression

```yaml
# agentest.yaml, used with --config agentest.yaml
disable: [X-003]   # reported as n/a, detail "disabled by config"
```

Keep suppressions in version control with a reason and an issue link.

## Reporting a false positive

Open an issue at <https://github.com/srpadmanabhuni/agentest/issues> with:

- agentest version (`agentest version`) and mode;
- the ID, the verdict and the full detail string;
- the smallest trace that reproduces it (OTLP/JSON; remove personal data), plus the card and tools if used;
- why the verdict is wrong, quoting the catalogue acceptance criteria.

A fix must keep `tests/test_agent_independence.py` passing; fixes that name a specific agent or tool are not
accepted.
