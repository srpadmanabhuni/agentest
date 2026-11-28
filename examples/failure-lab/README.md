# Failure Lab

Each folder takes one public agent example, tests one specific failure, and publishes the reproduction, the
observed behaviour, the agentest checks that catch it and a regression test. A finding is scoped to the
example and version it names; it is not a verdict on the framework.

| # | Question | Example | Checks |
|---|---|---|---|
| [001](001-refund-timeout-retry/) | Can this refund agent retry safely after a timeout? | OpenAI Agents SDK `examples/basic/stream_ws.py`, v0.26.0 | T2-003, T1-006, T1-011 |
| [002](002-note-injection/) | Does this refill agent obey an instruction hidden in a prescription note? | the bundled plain-Python refill agent (no model, no framework) | T4-003, T1-004, T4-012, X-019 |
| [003](003-claimed-add-to-cart/) | Did this shopping agent add the item to the cart? | bundled shopping agent `a22`, case 2 | T1-018 |

To reproduce a result, challenge a test or contribute a fix, see the folder's README or the issues labelled [failure-lab](https://github.com/srpadmanabhuni/agentest/issues?q=label%3Afailure-lab).

Each case is also a [failure registry](../../registry/README.md) entry ([001 is AFR-0001, 002 is AFR-0002, 003 is AFR-0003](../../docs/registry/INDEX.md)): a stable ID, a taxonomy category and the OWASP Agentic Top 10 entries the failing checks map to. A new case adds its entry in the same pull request.
