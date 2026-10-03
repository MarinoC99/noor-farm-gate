PYTHON ?= python3
VENV := .venv
VPY := $(VENV)/bin/python

.PHONY: verify eval demo

# Build the venv once; rebuild when requirements.txt changes.
$(VENV)/.stamp: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(VPY) -m pip install --quiet -r requirements.txt
	@touch $@

verify: $(VENV)/.stamp
	$(VPY) scripts/verify.py

eval:
	@echo "make eval: not built yet (Phase 2)" >&2; exit 1

demo:
	@echo "make demo: not built yet (Phase 1)" >&2; exit 1
