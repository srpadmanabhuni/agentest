# Course exercise: plan, review and run agent tests with the 110 checklist designs

For a class, a cohort or a team onboarding session (about 45 minutes). Learners turn the open
[Agentic AI Test Checklist 110](https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110)
into a test plan for one agent, review it by hand, then fill it with agentest verdicts.

- Notebook: [`agent_testing_course.ipynb`](agent_testing_course.ipynb) ([open in Colab](https://colab.research.google.com/github/srpadmanabhuni/agentest/blob/main/examples/course/agent_testing_course.ipynb))
- Script: [`test_plan.py`](test_plan.py), standard library only
- Guide: [Test planning with the checklist](../../docs/guides/TEST-PLANNING-WITH-THE-CHECKLIST.md)

```bash
python examples/course/test_plan.py --priority P0 --stage tool --out plan.csv
python examples/course/test_plan.py --ids T1-018,T2-001,T4-003,T7-014 --verdicts-from refill_bot_buggy --out plan.csv
```

Offline by default: the script reads the checklist rows bundled in this repo. `--hub` loads the same rows from
Hugging Face at one pinned revision through the `datasets` cache (fetched once, reused after), for courses that
want learners to work with the published dataset directly. Nothing fetches the dataset in a loop or on a schedule.

Exercises:

1. Pick your agent's stage (`tool`, `memory`, `output`, `plan`, `handover`, `side_effect`) and list its P0 tests.
2. For each row, write who owns it and which fixture you need (`fixture_needed`). Mark `manual_review_done` after
   you have walked the acceptance criteria by hand against one real conversation.
3. Fill verdicts from the bundled buggy refill agent and explain each `fail` from its `agentest_detail`.
4. Swap to the fixed agent (`--verdicts-from refill_bot`) and compare.
5. Pick one design that agentest cannot judge on your traces (`n/a`) and sketch how you would implement it in your
   own harness. If you build it, enhance and contribute: open a [new test idea](https://github.com/srpadmanabhuni/agentest/issues/new/choose).
