# Developer shortcuts. Everything here is offline and deterministic.
PYTHON ?= python
BASE ?= main

.PHONY: eval test lint

# Run every check on the public example agents; print a per-check verdict summary and the
# verdicts that differ from $(BASE) (default: main). Reads only agents/ and examples/*/agents/.
eval:
	$(PYTHON) scripts/eval_verdicts.py --base $(BASE) $(EVAL_ARGS)

test:
	$(PYTHON) -m pytest -q

lint:
	ruff check .
