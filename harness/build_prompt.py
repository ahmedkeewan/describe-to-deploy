#!/usr/bin/env python3
"""
Builds harness system prompts for a given mode from catalog/capabilities.json.

Generated, not hand-maintained, so the prompt can never drift from the catalog file itself
(the "derive-from-settings.json" principle in VOCAB.md 6c) -- add a capability to the JSON and
every future harness run picks it up automatically, no separate prompt edit required.

Usage:
  python3 harness/build_prompt.py --mode single-agent > /tmp/prompt.txt
  python3 harness/build_prompt.py --mode planner-executor --role planner  > /tmp/planner-prompt.txt
  python3 harness/build_prompt.py --mode planner-executor --role executor > /tmp/executor-prompt.txt

single-agent: capability catalog + conservative fallback rule, single agent plans and acts in one
pass.
planner-executor: splits that single pass into two agents -- a planner that ONLY produces a
stack-plan.json (see harness/stack-plan.schema.json) and never touches Floci's write APIs, and an
executor that reads a plan file and never sees the founder's original request text at all. The
split forces the plan itself to be an inspectable artifact you can read, gate, or hand to a
different agent, before anything real happens -- see research/history/GAME_PLAN.md's architecture table, "Planner"
and "Executor" rows.
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
        "text as one line to /tmp/floci-fallback-log.jsonl (JSON: {\"request\": "
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


def _catalog_for_planning(catalog: dict) -> list:
    """Slim view for the planner: it needs ids/phrases/deps to choose from, not the executor's
    provision.steps or verify.cli -- keeping those out forces the plan to name WHAT, not HOW."""
    return [
        {
            "id": c["id"],
            "phrases": c["phrases"],
            "depends_on": c.get("depends_on", []),
        }
        for c in catalog["capabilities"]
    ]


def build_fix2_planner_prompt() -> str:
    catalog = json.loads(CATALOG_PATH.read_text())
    schema = json.loads((REPO_ROOT / "harness" / "stack-plan.schema.json").read_text())

    lines = []
    lines.append(
        "You are the PLANNER half of a two-agent harness. A non-technical founder has made a "
        "plain-language product request. Your ONLY job is to turn it into a structured plan file "
        "-- you never provision anything yourself. A separate executor agent, which will not see "
        "the founder's original words at all, reads your plan file and does the actual work."
    )
    lines.append("")
    lines.append(
        "You have Bash available, but use it ONLY to inspect existing state on the local Floci "
        "emulator (http://localhost:4566, AWS CLI with AWS_ACCESS_KEY_ID=test, "
        "AWS_SECRET_ACCESS_KEY=test, AWS_DEFAULT_REGION=us-east-1) so your plan can correctly set "
        "reused_existing when appropriate. NEVER create, modify, or delete anything on Floci "
        "yourself -- read-only calls only (list/describe/get)."
    )
    lines.append("")
    lines.append(
        "## Capability catalog (what you may plan against)\n\n"
        "This is the ONLY set of things the executor knows how to build. Match the founder's "
        "request to entries BY MEANING, not exact string match."
    )
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(_catalog_for_planning(catalog), indent=2))
    lines.append("```")
    lines.append("")
    lines.append(
        "## The fallback rule -- this is not optional\n\n"
        "If the request does not clearly match a capability above (including anything resembling "
        f"{json.dumps(catalog['explicitly_not_covered']['examples'])}): produce a plan with an "
        "EMPTY matched_capabilities list and a filled-in `fallback` block naming the closest "
        "capability id (or null) and an exact plain-language question/statement for the founder. "
        "Do not invent a capability that isn't in the catalog above."
    )
    lines.append("")
    lines.append(
        "## Output: write your plan to the exact path given in your task, matching this schema\n\n"
        "```json\n" + json.dumps(schema["example"], indent=2) + "\n```\n\n"
        "For a fallback case, use this shape instead:\n\n"
        "```json\n" + json.dumps(schema["fallback_shape"], indent=2) + "\n```\n\n"
        "Field notes: " + json.dumps(schema["field_notes"], indent=2)
    )
    lines.append("")
    lines.append(
        "When you're done, report back in one short sentence confirming the plan file was "
        "written and its path. Do not describe the plan's contents in founder language -- that's "
        "the executor's job, after it actually does the work."
    )
    return "\n".join(lines)


def build_fix2_executor_prompt() -> str:
    catalog = json.loads(CATALOG_PATH.read_text())

    lines = []
    lines.append(
        "You are the EXECUTOR half of a two-agent harness. A separate planner agent has already "
        "turned a non-technical founder's request into a structured plan file -- you have NOT "
        "seen the founder's original words, only the plan. Read the plan file at the path given "
        "in your task and carry it out exactly."
    )
    lines.append("")
    lines.append(
        "You have Bash available. Reach Floci with the AWS CLI: "
        "AWS_ENDPOINT_URL=http://localhost:4566, AWS_ACCESS_KEY_ID=test, "
        "AWS_SECRET_ACCESS_KEY=test, AWS_DEFAULT_REGION=us-east-1."
    )
    lines.append("")
    lines.append(
        "## Full capability catalog (how to build each thing the plan may reference)\n\n"
        "For each `capability_id` in the plan's `matched_capabilities` list, IN ORDER, look up "
        "the matching entry below and follow its `provision.steps` using the plan's "
        "`resource_name` for that entry, skipping provisioning (but still verifying) if "
        "`reused_existing` is true. Then run its `verify.cli` for real before moving to the next "
        "entry or declaring anything done."
    )
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(catalog["capabilities"], indent=2))
    lines.append("```")
    lines.append("")
    lines.append(
        "## If the plan has a non-null `fallback` block\n\n"
        "Do not provision anything. Your entire final report to the founder is the plan's "
        "`fallback.question_for_founder` text, relayed as-is (light rewording for tone is fine, "
        "meaning must not change)."
    )
    lines.append("")
    lines.append(
        "## Reporting back to the founder\n\n"
        "Your final report must ONLY use plain, founder-facing language. NEVER name the "
        "underlying AWS/Floci service, port, ARN, resource name, endpoint URL, or any other infra "
        "term. A jargon leak is a failure even if the infrastructure works perfectly."
    )
    lines.append("")
    lines.append(
        "## Before claiming anything is done\n\n"
        "Actually run each capability's `verify.cli` (or the clear real-world equivalent) against "
        "the live Floci endpoint and confirm it succeeds. Never report something as working "
        "because the plan said to build it -- only because you checked it actually works, "
        "including for anything the plan marked `reused_existing`."
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=["single-agent", "planner-executor"], default="single-agent"
    )
    parser.add_argument("--role", choices=["planner", "executor"], default=None)
    args = parser.parse_args()
    if args.mode == "single-agent":
        print(build_fix1_prompt())
    elif args.mode == "planner-executor":
        if args.role == "planner":
            print(build_fix2_planner_prompt())
        elif args.role == "executor":
            print(build_fix2_executor_prompt())
        else:
            raise SystemExit("--mode planner-executor requires --role planner|executor")


if __name__ == "__main__":
    main()
