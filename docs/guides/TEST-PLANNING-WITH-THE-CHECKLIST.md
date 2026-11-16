# Test planning and manual review with the 110 checklist designs

**Use the open [Agentic AI Test Checklist 110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110) as a test plan, a manual review procedure and a design source for your own harness, then let agentest judge the checks it can judge from your traces.**

Each of the 110 rows is a test design: objective, acceptance criteria, pass and fail signals, the fixture you need, severity, priority and the agent stage it applies to. You do not need agentest to use them.

## 1. Make a test plan in one command

```bash
python examples/course/test_plan.py --priority P0 --stage tool --out plan.csv
```

`plan.csv` has one row per test with empty `owner` and `manual_review_done` columns for your team. Filters: `--ids`, `--priority P0|P1|P2`, `--stage tool|memory|output|plan|handover|side_effect`, `--class-id T1..T7`. The script reads the rows bundled in this repo, offline. `--hub` reads the published dataset at one pinned revision instead (`pip install datasets`; cached after the first fetch).

Or in three lines of Python from the Hub:

```python
from datasets import load_dataset
ds = load_dataset("srinivaspadmanabhuni/agentic-ai-test-checklist-110", "p0_smoke", split="train")
print(ds[0]["id"], ds[0]["title"])
```

## 2. Review by hand before you automate

For each planned row, take one real conversation of your agent and walk the acceptance criteria against it. The dataset ships manual procedures for this (`docs/MANUAL-PROCEDURES.md` on the dataset page). A manual pass is how you find out whether the design fits your agent before you spend time on fixtures. Record it in `manual_review_done`.

## 3. Fill the plan with agentest verdicts

```bash
python examples/course/test_plan.py --ids T1-018,T2-001,T4-003,T7-014 --verdicts-from refill_bot_buggy --out plan.csv
```

This runs agentest on a bundled sample agent and writes `agentest_verdict` and `agentest_detail` next to each design. On your own agent, run `agentest std run --otlp your_trace.otlp.json --card your-agent-card.json --tools your-tools.json --format csv` and join on `id`. A check with no evidence in your trace says `n/a`, never a silent `pass`.

## 4. Implement a design in your own harness

Some designs need fixtures agentest cannot see in a trace (a store snapshot, a crash point, a paraphrase pair). Implement those in the harness you already use, keyed by the same test ID so results line up:

- **pytest:** `examples/pytest_skeleton.py` on the dataset page, and [`templates/test_langgraph.py`](../../templates/test_langgraph.py) here.
- **Eval harnesses:** the snippets in [`examples/integrations/`](../../examples/integrations/README.md) read the checklist rows as test cases.
- **CI:** gate on the IDs you automated with `--strict` ([tutorial 4](../tutorials/04-ci-cd-github-actions.md)).

If you implement a design, enhance and contribute: open a [new test idea](https://github.com/srpadmanabhuni/agentest/issues/new/choose) or a pull request with the ID in the title, and you will be credited in the release notes.

## For courses and cohorts

[`examples/course/`](../../examples/course/README.md) has a 45-minute exercise and a notebook built on these steps. Pin the dataset revision in course material so every learner sees the same rows.
