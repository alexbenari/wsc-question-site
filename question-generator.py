#!/usr/bin/env python3
"""CLI wrapper for Codex-based WSC question generation."""

from __future__ import annotations

import argparse
import subprocess
import sys
import shutil
from pathlib import Path


BATCH_PROMPT_FILE = Path("codex-question-generation-batch-prompt.md")
VALIDATOR_FILE = Path("validate-question-pool.py")
TOPICS_DIR = Path("topics")
FLOWS_DIR = Path("flows")

SINGLE_DEFAULT_CATEGORIES = "single_topic_understanding,context_clues"
DEFAULT_FLOW_RULES = "- No additional flow-specific rules."
ARTWORKS_FLOW = "artworks"
ARTWORKS_FLOW_ALIASES = {ARTWORKS_FLOW, "artwoks", "artowrks"}


def build_generation_prompt(
    question_count: int,
    categories: str,
    output_file: str,
    scope_source: str,
    scope_profile: str,
    flow_rules: str = DEFAULT_FLOW_RULES,
) -> str:
    if not BATCH_PROMPT_FILE.exists():
        raise FileNotFoundError(f"Missing prompt file: {BATCH_PROMPT_FILE}")
    if not TOPICS_DIR.exists():
        raise FileNotFoundError(f"Missing topics dir: {TOPICS_DIR}")

    prompt = BATCH_PROMPT_FILE.read_text(encoding="utf-8")
    prompt = prompt.replace("<QUESTION_COUNT>", str(question_count))
    prompt = prompt.replace("<CATEGORY_LIST_OR_ALL>", categories)
    prompt = prompt.replace("<OUTPUT_FILE>", output_file)
    prompt = prompt.replace("<SCOPE_SOURCE>", scope_source)
    prompt = prompt.replace("<SCOPE_PROFILE>", scope_profile)
    prompt = prompt.replace("<FLOW_RULES>", flow_rules)
    return prompt


def run_codex(prompt: str, search: bool, full_auto: bool) -> int:
    codex_bin = shutil.which("codex") or shutil.which("codex.cmd") or shutil.which("codex.exe")
    if not codex_bin:
        print("Could not find 'codex' executable in PATH.")
        return 1

    cmd = [codex_bin]
    if search:
        cmd.append("--search")
    cmd.extend(["exec"])
    if full_auto:
        cmd.append("--full-auto")
    cmd.extend(["--cd", ".", "-"])

    proc = subprocess.run(cmd, input=prompt, text=True)
    return proc.returncode


def run_validator_non_fatal(input_file: Path, categories: str) -> None:
    if not VALIDATOR_FILE.exists():
        print(f"Validator file not found, skipping final validation: {VALIDATOR_FILE}")
        return
    if not input_file.exists():
        print(f"Output file not found, skipping final validation: {input_file}")
        return

    cmd = [
        sys.executable,
        str(VALIDATOR_FILE),
        "--input",
        str(input_file),
        "--topics-dir",
        str(TOPICS_DIR),
        "--allowed-categories",
        categories,
    ]
    rc = subprocess.run(cmd, text=True).returncode
    if rc != 0:
        print(
            "\nFinal validation reported issues. Output file is kept.\n"
            f"Output file: {input_file}"
        )
    else:
        print("\nFinal validation passed.")


def load_flow_rules(flow_file: Path) -> str:
    if not flow_file.exists():
        raise FileNotFoundError(f"Missing flow rules file: {flow_file}")
    flow_rules = flow_file.read_text(encoding="utf-8").strip()
    if not flow_rules:
        raise FileNotFoundError(f"Flow rules file is empty: {flow_file}")
    return flow_rules


def normalize_flow_name(raw_flow: str) -> str:
    flow = raw_flow.strip().lower()
    if not flow:
        return ""
    if flow in ARTWORKS_FLOW_ALIASES:
        return ARTWORKS_FLOW
    return flow


def get_flow_file(flow_name: str) -> Path:
    return FLOWS_DIR / f"flow-{flow_name}.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate WSC questions via Codex prompts.")
    sub = parser.add_subparsers(dest="mode", required=True)

    single = sub.add_parser("single", help="Generate questions for a single topic.")
    single.add_argument("--topic", required=True, help="Topic slug under topics/<slug>/topic.json")
    single.add_argument("--count", type=int, required=True, help="Number of questions to generate.")
    single.add_argument(
        "--output",
        default="",
        help="Output JSONL path. Default: question-pool-<topic>.jsonl",
    )
    single.add_argument(
        "--categories",
        default=SINGLE_DEFAULT_CATEGORIES,
        help=(
            "Comma-separated categories (default: single-topic categories). "
            "If 'all', this is normalized to single-topic categories."
        ),
    )
    single.add_argument("--no-search", action="store_true", help="Disable codex --search.")
    single.add_argument("--no-full-auto", action="store_true", help="Disable codex --full-auto.")
    single.add_argument(
        "--no-final-validate",
        action="store_true",
        help="Skip the wrapper's final non-fatal validator run.",
    )

    batch = sub.add_parser("batch", help="Generate full question pool across topics.")
    batch.add_argument("--count", type=int, required=True, help="Number of questions to generate.")
    batch.add_argument(
        "--output",
        default="question-pool.jsonl",
        help="Output JSONL path (default: question-pool.jsonl).",
    )
    batch.add_argument(
        "--categories",
        default="all",
        help="Comma-separated categories or 'all' (default).",
    )
    batch.add_argument(
        "--flow",
        default="",
        help="Optional flow profile name. Example: artworks (loads flows/flow-artworks.md).",
    )
    batch.add_argument("--no-search", action="store_true", help="Disable codex --search.")
    batch.add_argument("--no-full-auto", action="store_true", help="Disable codex --full-auto.")
    batch.add_argument(
        "--no-final-validate",
        action="store_true",
        help="Skip the wrapper's final non-fatal validator run.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.mode == "single":
            categories = args.categories.strip()
            if categories.lower() == "all":
                categories = SINGLE_DEFAULT_CATEGORIES
            if args.count <= 0:
                print("--count must be > 0")
                return 1
            topic_json = TOPICS_DIR / args.topic / "topic.json"
            if not topic_json.exists():
                print(f"Missing topic file: {topic_json}")
                return 1
            scope_source = str(topic_json)
            scope_profile = "\n".join(
                [
                    "- Single-topic scope: use only this topic file.",
                    "- Use categories: single_topic_understanding, context_clues.",
                    "- Do NOT use comparative_consequences or thematic_synthesis in single-topic scope.",
                    "- Every question must include exactly one topic in `topics`, matching this topic title.",
                    "- Source fidelity remains mandatory against this topic's extracted fields.",
                ]
            )
            output_file = Path(args.output.strip() or f"question-pool-{args.topic}.jsonl")
            prompt = build_generation_prompt(
                args.count,
                categories,
                str(output_file),
                scope_source,
                scope_profile,
                flow_rules=DEFAULT_FLOW_RULES,
            )
            rc = run_codex(prompt, search=not args.no_search, full_auto=not args.no_full_auto)
            if rc != 0:
                return rc
            if not args.no_final_validate:
                run_validator_non_fatal(output_file, categories)
            return 0

        if args.mode == "batch":
            categories = args.categories.strip()
            flow_name = normalize_flow_name(args.flow)
            if args.count <= 0:
                print("--count must be > 0")
                return 1
            if categories.lower() != "all" and not categories:
                print("--categories cannot be empty")
                return 1
            scope_source = "topics/ (all topics/*/topic.json)"
            scope_profile = "\n".join(
                [
                    "- Multi-topic scope: use all topic files under topics/ unless category constraints narrow usage.",
                    "- For comparative_consequences and thematic_synthesis, use exactly 2 topics per question.",
                    "- For single_topic_understanding and context_clues, prefer exactly 1 topic per question.",
                ]
            )
            flow_rules = DEFAULT_FLOW_RULES
            if flow_name:
                flow_rules = load_flow_rules(get_flow_file(flow_name))

            default_output = "question-pool.jsonl"
            if flow_name == ARTWORKS_FLOW:
                default_output = "question-pool-artworks.jsonl"
            elif flow_name:
                default_output = f"question-pool-{flow_name}.jsonl"

            output_file = Path(args.output.strip() or default_output)
            prompt = build_generation_prompt(
                args.count,
                categories,
                str(output_file),
                scope_source,
                scope_profile,
                flow_rules=flow_rules,
            )
            rc = run_codex(prompt, search=not args.no_search, full_auto=not args.no_full_auto)
            if rc != 0:
                return rc
            if not args.no_final_validate:
                run_validator_non_fatal(output_file, categories)
            return 0
    except FileNotFoundError as exc:
        print(str(exc))
        return 1

    print("Unknown mode")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
