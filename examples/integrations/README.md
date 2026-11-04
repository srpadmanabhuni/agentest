# Integration snippets (external tools)

Examples for using the agentest checklist dataset in other eval tools. These tools are NOT agentest dependencies; install them separately.

| File | Tool | Tested offline (4 Nov 2026) |
|---|---|---|
| inspect_ai_task.py | inspect-ai | yes: `inspect eval inspect_ai_task.py --model mockllm/model --model-role grader=mockllm/model --limit 3` |
| lm_eval_agentest_examples.yaml | lm-evaluation-harness | yes: `lm_eval --model dummy --tasks agentest_checklist_examples --include_path . --limit 3` |
| deepeval_goldens.py | DeepEval | yes: builds 404 Goldens (no API key) |
| promptfoo_tests_from_hf.py + promptfooconfig.yaml | promptfoo | yes: echo provider with promptfooconfig.smoke.yaml (contains-assert), 3/3 pass; llm-rubric needs your own grader |

See LINKS.md and LISTING.md. Contact: srinivas AT testAIng.com
