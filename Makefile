.PHONY: help setup test board

help:
	@echo "make setup  - run ./setup.sh (Docker/Colima + Floci + venv + MCP wiring)"
	@echo "make test   - run the harness unit test suite"
	@echo "make board  - start the live board (./setup.sh --start-board)"

setup:
	./setup.sh

test:
	python3 -m unittest discover -s harness/tests

board:
	./setup.sh --start-board
