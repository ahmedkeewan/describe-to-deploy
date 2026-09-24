# Contributing

Thanks for your interest in this project.

## Getting set up

Run `./setup.sh` from the repo root — it checks for Docker/Colima, installs Floci if needed, sets
up the harness's Python virtual environment, and wires the MCP server into Claude Desktop, Claude
Code, and Cursor. See [`harness/README.md`](harness/README.md) for what it does and the manual
steps it automates.

## Running the tests

```bash
cd harness && python3 -m unittest discover -s tests
```

Some tests require the `mcp` package from `harness/requirements.txt` — activate `harness/.venv`
first (`source harness/.venv/bin/activate`) if `setup.sh` created one for you.

## Making a change

1. Open an issue describing the change before starting significant work, so we can agree on the
   approach first.
2. Create a branch off `main`.
3. Keep changes focused — one logical change per pull request.
4. Run the test suite locally before opening a PR; a PR with failing tests won't be reviewed.
5. Describe what changed and why in the PR description, and link the issue it addresses.

## Reporting bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your platform (macOS, Linux, or WSL)

## Code of conduct

Be respectful and constructive. This is a small research/engineering project — assume good faith
and keep feedback focused on the work.
