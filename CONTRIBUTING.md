# Contributing

Thanks for your interest in Service Buddy.

## Getting set up

Run `./setup.sh` from the repo root. It checks for Docker/Colima, installs Floci if needed, sets
up the harness's Python virtual environment in `harness/.venv`, and wires the MCP server into
Claude Code, Cursor, and Claude Desktop. The prerequisites are listed in the
[README's Quickstart](README.md#quickstart). See [`harness/README.md`](harness/README.md) for what
setup does and the manual steps it automates.

## Running the tests

```bash
make test
```

This runs the suite in `harness/tests/` with the Python in `harness/.venv`, so run `./setup.sh`
first. None of the tests need Floci running.

## Good first contributions: add a capability

The easiest way to extend Service Buddy is to add an entry to
[`catalog/capabilities.json`](catalog/capabilities.json). Each entry maps a plain-language need
("let people upload photos") to the steps that set it up and a real check that proves it works.
[`catalog/README.md`](catalog/README.md) describes every field. A good entry:

1. Describes the need the way a founder would ask for it, in `phrases` and
   `founder_description`, without naming any AWS service.
2. Has a `verify.cli` check that exercises the capability for real (write something and read it
   back, not just "the resource exists"), and a `verify.founder_proof` sentence saying what the
   check did in plain language.
3. Has been run against a local Floci (`aws --endpoint-url=http://localhost:4566`) and passes.
   Say in the PR what you ran.

Requests the server couldn't match are a good source of ideas; see `explicitly_not_covered` in the
catalog for known gaps.

## Making a change

1. Open an issue describing the change before starting significant work, so we can agree on the
   approach first.
2. Create a branch off `main`.
3. Keep changes focused: one logical change per pull request.
4. Run `make test` before opening a PR. A PR with failing tests won't be reviewed.
5. Describe what changed and why in the PR description, and link the issue it addresses.

## Reporting bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your platform (macOS, Linux, or WSL)

## Code of conduct

Be respectful and constructive. This is a small open-source project, so assume good faith and keep
feedback focused on the work. The full [Code of Conduct](CODE_OF_CONDUCT.md) applies.
