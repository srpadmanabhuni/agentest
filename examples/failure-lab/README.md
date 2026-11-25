# Failure Lab

Each folder takes one public agent example, tests one specific failure, and publishes the reproduction, the
observed behaviour, the agentest checks that catch it and a regression test. A finding is scoped to the
example and version it names; it is not a verdict on the framework.

| # | Question | Example | Checks |
|---|---|---|---|
| [001](001-refund-timeout-retry/) | Can this refund agent retry safely after a timeout? | OpenAI Agents SDK `examples/basic/stream_ws.py`, v0.26.0 | T2-003, T1-006, T1-011 |

To reproduce a result, challenge a test or contribute a fix, see the folder's README or the issues labelled [failure-lab](https://github.com/srpadmanabhuni/agentest/issues?q=label%3Afailure-lab).
