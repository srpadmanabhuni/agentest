# Developer shortcuts. Everything here is offline and deterministic.
PYTHON ?= python
BASE ?= main

.PHONY: eval test lint llms-full

# Run every check on the public example agents; print a per-check verdict summary and the
# verdicts that differ from $(BASE) (default: main). Reads only agents/ and examples/*/agents/.
eval:
	$(PYTHON) scripts/eval_verdicts.py --base $(BASE) $(EVAL_ARGS)

test:
	$(PYTHON) -m pytest -q

lint:
	ruff check .

# Rebuild the AI-crawler bundle from the README, install docs, CLI flags and test IDs.
llms-full:
	PYTHONPATH=src $(PYTHON) scripts/gen_llms_full.py
