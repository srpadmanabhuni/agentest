# Post a redacted agent report

Run this example from the repository root after installing agentest. The bundled trace is synthetic. The check runs offline and writes a Markdown report to `report.md` in the current directory.

```bash
agentest std run --otlp examples/first_trace/trace.otlp.json --tools examples/first_trace/tools.json --format md --out report.md
grep -F 'T5-007 | fail' report.md
```

In the example, the recorded call to `mark_reviewed` has `confirm` set to false. T5-007 flags that write. Open the report and find the row for the check you want to discuss.

## Prepare the excerpt

Copy the relevant rows into a new draft. Check the evidence text as well as the headings before sharing.

- Remove secrets, API keys, tokens and authorization headers.
- Replace personal details such as names, email addresses and phone numbers with fictional values.
- Replace customer names, account identifiers and record contents with synthetic examples.
- Remove private URLs, including internal hostnames and identifying query parameters.

## Share your findings

Post the reviewed excerpt in [Post your agent report](https://github.com/srpadmanabhuni/agentest/discussions/30). Name the framework that recorded the trace (or say you used the bundled example), list any check IDs whose verdicts look wrong, and describe any missing check. Explain what surprised you and what you expected to see.

For an incorrect failure, use the [false-positive form](https://github.com/srpadmanabhuni/agentest/issues/new?template=false-positive.yml). To propose a missing check, use the [new-test-idea form](https://github.com/srpadmanabhuni/agentest/issues/new?template=new-test-idea.yml).

Back to the [walkthrough index](README.md).
