# "Tested with agentest" badge

If you check your agent's traces with agentest, you can add this badge to your README:

[![tested with agentest](https://img.shields.io/badge/tested%20with-agentest-2ea44f)](https://github.com/srpadmanabhuni/agentest)

## Copy the snippet

Markdown:

```markdown
[![tested with agentest](https://img.shields.io/badge/tested%20with-agentest-2ea44f)](https://github.com/srpadmanabhuni/agentest)
```

HTML:

```html
<a href="https://github.com/srpadmanabhuni/agentest"><img alt="tested with agentest" src="https://img.shields.io/badge/tested%20with-agentest-2ea44f"></a>
```

reStructuredText:

```rst
.. image:: https://img.shields.io/badge/tested%20with-agentest-2ea44f
   :target: https://github.com/srpadmanabhuni/agentest
   :alt: tested with agentest
```

## What the badge means

It means your project runs agentest on its agent traces, ideally in CI. It does not mean certification, and it does not mean every check passes. If you want a line to go with it, you could say what you run, for example: "CI runs `agentest std run --otlp traces/*.jsonl` on every pull request."

## Add agentest to your project

Install from PyPI:

```bash
pip install agentest-ai
```

Then, from a clone, run it on the sample trace that ships in the repository:

```bash
agentest std run --otlp examples/first_trace/trace.otlp.json --tools examples/first_trace/tools.json --format md
```

Swap in your own trace file.

To run it in CI, use the GitHub Action [srpadmanabhuni/agentest-action](https://github.com/srpadmanabhuni/agentest-action) or follow [GitHub Action](developers/GITHUB-ACTION.md).

Using the badge? Tell us in [Discussions](https://github.com/srpadmanabhuni/agentest/discussions).
