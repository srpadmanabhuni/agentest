# agentest checklist: canonical links

- GitHub repo: https://github.com/srpadmanabhuni/agentest  (package name `agentest-ai`; not on PyPI yet, install from git: `pip install git+https://github.com/srpadmanabhuni/agentest`)
- HF dataset: https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110  (v1.4.0: 110 core tests + 5 responsible-AI additions)
- HF Spaces: https://huggingface.co/spaces/srinivaspadmanabhuni/agentic-ai-test-checklist-demo · https://huggingface.co/spaces/srinivaspadmanabhuni/agentic-ai-reference-agents-viewer
- Citation DOI: https://doi.org/10.5281/zenodo.23597877
- Contact: srinivas AT testAIng.com

## Dataset configs (verified live via datasets-server, 4 Nov 2026; all split `train`)
There is no `default` config; the full checklist is `all`.
`all`, `enriched`, `p0_smoke`, `examples`, `traces`, `golden`, `rai_additions`, `crash_recovery_variants`, and per-pack configs
`functional`, `security`, `privacy`, `reliability_robustness`, `orchestration`, `data_lineage`, `explainability`, `bias_fairness`, `responsible_ai`, `compliance_governance`.

- `examples` (404 rows): test_id, example_id, example_type, scenario, input, expected_behavior, fail_signal, severity, pack, title, synthetic
- `traces`: trace_id, test_id, agent_type, trace, label, explanation, synthetic, generator, label_provenance, notes
- `rai_additions`: id, class_id, class_name, eval_group, rai_group, title, objective, acceptance_criteria, oracle_type, severity, priority, … control_refs
- `golden`: file golden/golden-cases-v1.jsonl (the viewer can't extract its columns yet; load the JSONL directly)
- Raw CSV for examples: https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110/resolve/main/examples/examples-v1.3.0.csv
