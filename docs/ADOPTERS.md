# Adopters

Share a run of agentest on your own agent in GitHub Discussions. Post it in [Show and tell](https://github.com/srpadmanabhuni/agentest/discussions/categories/show-and-tell). The open thread is [Tried agentest on your own agent? Share what it caught or missed](https://github.com/srpadmanabhuni/agentest/discussions/265).

## How to share a run

Install from PyPI:

```bash
pip install agentest-ai
```

Point it at a recorded trace of your own:

```bash
agentest std run --otlp your_trace.otlp.json --card your-agent-card.json --tools your-tools.json --format md
```

If you already have an agent folder, this is the same command:

```bash
agentest std run --agents your_agents --agent your_agent --format md
```

Comment on [Discussion #265](https://github.com/srpadmanabhuni/agentest/discussions/265) with this short template. Redact secrets, keys and personal data before you post.

```text
- Framework (LangGraph, AutoGen, smolagents, plain Python, or other):
- Trace format (OTLP/JSON, or another export you imported):
- What it caught (check IDs and a short description):
- What it missed (behaviour you expected to be flagged):
- Rough edges (unclear docs, a verdict that looked wrong, or something hard to set up):
```

If something was missed, open a new issue with the [New test idea](https://github.com/srpadmanabhuni/agentest/issues/new?template=new-test-idea.yml) or [False negative](https://github.com/srpadmanabhuni/agentest/issues/new?template=false-negative.yml) form, and link it from your comment. If a verdict looked wrong, use the [False positive](https://github.com/srpadmanabhuni/agentest/issues/new?template=false-positive.yml) form.

## Badge

If your project runs agentest on its agent traces, add the badge from ["Tested with agentest"](TESTED-WITH-AGENTEST.md). The badge means your project runs agentest on its traces, ideally in CI. The snippet to copy is on that page.

## Where to look next

- [Use cases](../examples/use_cases/README.md): one recorded failure per case, with the command and the printed result.
- [Wall of caught failures](WALL-OF-CAUGHT-FAILURES.md): the same runs, with the full printed tables.
- [Roadmap](ROADMAP.md), pinned as [issue #272](https://github.com/srpadmanabhuni/agentest/issues/272). Suggestions go on [Discussion #80](https://github.com/srpadmanabhuni/agentest/discussions/80).
