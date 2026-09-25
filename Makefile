.PHONY: help setup test board down venv-check

VENV_PYTHON := harness/.venv/bin/python3

help:
	@echo "make setup  - run ./setup.sh (Docker/Colima + Floci + AWS CLI + venv + MCP wiring)"
	@echo "make test   - run the harness unit test suite (needs 'make setup' first)"
	@echo "make board  - start the live board at http://localhost:7777 (needs 'make setup' first)"
	@echo "make down   - stop Floci (floci stop); non-destructive, leaves containers/state intact"

setup:
	./setup.sh

test: venv-check
	$(VENV_PYTHON) -m unittest discover -s harness/tests

# Runs the board directly instead of re-running all of setup. FLOCI_BOARD_PORT, if set,
# passes through unchanged (plain environment inheritance), same as ./setup.sh --start-board.
board: venv-check
	@echo "Open http://localhost:$${FLOCI_BOARD_PORT:-7777} -- press Ctrl+C here to stop it."
	@exec $(VENV_PYTHON) harness/web_server.py

venv-check:
	@test -x $(VENV_PYTHON) || { echo "No harness/.venv yet -- run 'make setup' first."; exit 1; }

down:
	@if command -v floci >/dev/null 2>&1; then \
		FLOCI_BIN=floci; \
	elif command -v floci-cli >/dev/null 2>&1; then \
		FLOCI_BIN=floci-cli; \
	else \
		echo "Floci isn't installed -- nothing to stop."; \
		exit 0; \
	fi; \
	if "$$FLOCI_BIN" stop; then \
		echo "Floci stopped."; \
	else \
		echo "'$$FLOCI_BIN stop' failed -- Floci may not be running. Nothing else to do."; \
	fi
