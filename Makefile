.PHONY: help setup test board down

help:
	@echo "make setup  - run ./setup.sh (Docker/Colima + Floci + venv + MCP wiring)"
	@echo "make test   - run the harness unit test suite"
	@echo "make board  - start the live board (./setup.sh --start-board)"
	@echo "make down   - stop Floci (floci stop); non-destructive, leaves containers/state intact"

setup:
	./setup.sh

test:
	python3 -m unittest discover -s harness/tests

board:
	./setup.sh --start-board

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
