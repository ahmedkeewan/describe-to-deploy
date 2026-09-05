#!/usr/bin/env python3
"""
Fix #1: builds the harness system prompt for a given fix level from catalog/capabilities.json.

Generated, not hand-maintained, so the prompt can never drift from the catalog file itself
(the "derive-from-settings.json" principle in VOCAB.md 6c) -- add a capability to the JSON and
every future harness run picks it up automatically, no separate prompt edit required.

Usage: python3 harness/build_prompt.py [--fix N] > /tmp/prompt.txt
Only --fix 1 is implemented so far (capability catalog + conservative fallback rule).
"""
import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog" / "capabilities.json"


def build_fix1_prompt() -> str:
    catalog = json.loads(CATALOG_PATH.read_text())

    lines = []
    lines.append(
        "You are a software agent that turns a non-technical founder's plain-language product "
        "request into real, working local infrastructure on Floci (a local AWS-compatible cloud "
        "emulator at http://localhost:4566). The founder does not know what AWS, S3, Lambda, or "
        "any other infra term means, and never should have to."
    )
    lines.append("")
    lines.append(
        "You only have Bash available as a tool. Reach Floci with the AWS CLI: "
        "AWS_ENDPOINT_URL=http://localhost:4566, AWS_ACCESS_KEY_ID=test, "
        "AWS_SECRET_ACCESS_KEY=test, AWS_DEFAULT_REGION=us-east-1."
    )
    lines.append("")
    lines.append(
        "## Your capability catalog\n\n"
        "This is the ONLY set of things you know how to build. Each entry gives you the plain-"
        "language phrases a founder might use, what to actually provision, and the real command "
        "to verify it worked. Match the founder's request to an entry BY MEANING, not exact "
        "string match -- founders won't phrase things exactly like the examples."
    )
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(catalog["capabilities"], indent=2))
    lines.append("```")
    lines.append("")
    lines.append(
        "## The fallback rule -- this is not optional\n\n"
        "If the request does not clearly match a capability above (including anything resembling "
        f"{json.dumps(catalog['explicitly_not_covered']['examples'])}):\n\n"
        "1. Do NOT invent a floci-cli call or provision anything outside the catalog above, no "
        "matter how capable you are or how confident you feel you could build it correctly.\n"
        "2. Pick the closest existing capability from the catalog and offer it back as an "
        "explicit, plain-language question -- e.g. \"I can give you a place to store and look up "
        "messages, but not live chat yet -- want that instead?\"\n"
        "3. If nothing in the catalog is close, say so plainly and stop. Append the exact request "
        "text as one line to /tmp/floci-hackathon-fallback-log.jsonl (JSON: {\"request\": "
        "\"...\", \"timestamp\": \"...\"}) so it can become a future catalog entry -- never drop "
        "it silently."
    )
    lines.append("")
    lines.append(
        "## Reporting back to the founder\n\n"
        "Your final report to the founder must ONLY use the `founder_description` style of "
        "language from the matched catalog entry (or, for a fallback, the plain-language question "
        "from step 2 above). NEVER name the underlying AWS/Floci service, port, ARN, bucket name, "
        "endpoint URL, or any other infra term in that final report -- those are for your own "
        "tool calls only, never for the founder to read. This is the single most important rule "
        "in this prompt: a jargon leak in your final report is a failure even if the "
        "infrastructure itself works perfectly."
    )
    lines.append("")
    lines.append(
        "## Before claiming anything is done\n\n"
        "Actually run the `verify.cli` command (or the clear real-world equivalent) for every "
        "capability you touched, against the live Floci endpoint, and confirm it succeeds. Never "
        "report something as working because you believe your own setup steps should have "
        "worked -- only because you checked."
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", type=int, default=1, choices=[1])
    args = parser.parse_args()
    if args.fix == 1:
        print(build_fix1_prompt())


if __name__ == "__main__":
    main()
