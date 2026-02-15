#!/usr/bin/env python3
"""CLI wrapper for Codex-based WSC question generation."""

from __future__ import annotations

import argparse
import subprocess
import sys
import shutil
from pathlib import Path


SINGLE_PROMPT_FILE = Path("codex-question-generation-single-topic-prompt.md")
BATCH_PROMPT_FILE = Path("codex-question-generation-batch-prompt.md")
VALIDATOR_FILE = Path("validate-question-pool.py")
TOPICS_DIR = Path("topics")

SINGLE_DEFAULT_CATEGORIES = "single_topic_understanding,context_clues"
ALL_CATEGORIES = (
    "single_topic_understanding,context_clues,comparative_consequences,thematic_synthesis"
)


def build_single_prompt(topic_slug: str, question_count: int, categories: str, output_file: str) -> str:
    if not SINGLE_PROMPT_FILE.exists():
        raise FileNotFoundError(f"Missing prompt file: {SINGLE_PROMPT_FILE}")
    topic_json = TOPICS_DIR / topic_slug / "topic.json"
    if not topic_json.exists():
        raise FileNotFoundError(f"Missing topic file: {topic_json}")

    prompt = SINGLE_PROMPT_FILE.read_text(encoding="utf-8")
    prompt = prompt.replace("<TOPIC_SLUG>", topic_slug)
    prompt = prompt.replace("<QUESTION_COUNT>", str(question_count))
    prompt = prompt.replace("<CATEGORY_LIST_OR_ALL>", categories)
    prompt = prompt.replace("<OUTPUT_FILE>", output_file)
    return prompt


def build_batch_prompt(question_count: int, categories: str, output_file: str) -> str:
    if not BATCH_PROMPT_FILE.exists():
        raise FileNotFoundError(f"Missing prompt file: {BATCH_PROMPT_FILE}")
    if not TOPICS_DIR.exists():
        raise FileNotFoundError(f"Missing topics dir: {TOPICS_DIR}")

    prompt = BATCH_PROMPT_FILE.read_text(encoding="utf-8")
    prompt = prompt.replace("<QUESTION_COUNT>", str(question_count))
    prompt = prompt.replace("<CATEGORY_LIST_OR_ALL>", categories)
    prompt = prompt.replace("<OUTPUT_FILE>", output_file)
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


def run_validator(input_file: Path, categories: str, strict_warnings: bool) -> int:
    if not VALIDATOR_FILE.exists():
        print(f"Validator file not found: {VALIDATOR_FILE}")
        return 1
    if not input_file.exists():
        print(f"Generated question file not found: {input_file}")
        return 1

    cmd = [
        sys.executable,
        str(VALIDATOR_FILE),
        "--input",
        str(input_file),
        "--topics-dir",
        str(TOPICS_DIR),
        "--allowed-categories",
        categories,
        "--check-category-balance",
    ]
    if strict_warnings:
        cmd.append("--strict-warnings")
    proc = subprocess.run(cmd, text=True)
    return proc.returncode


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
        "--no-validate",
        action="store_true",
        help="Skip local validator after generation (validation is on by default).",
    )
    single.add_argument(
        "--strict-warnings",
        action="store_true",
        help="When validation runs, fail on validator warnings.",
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
    batch.add_argument("--no-search", action="store_true", help="Disable codex --search.")
    batch.add_argument("--no-full-auto", action="store_true", help="Disable codex --full-auto.")
    batch.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip local validator after generation (validation is on by default).",
    )
    batch.add_argument(
        "--strict-warnings",
        action="store_true",
        help="When validation runs, fail on validator warnings.",
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
            output_file = args.output.strip() or f"question-pool-{args.topic}.jsonl"
            prompt = build_single_prompt(args.topic, args.count, categories, output_file)
            rc = run_codex(prompt, search=not args.no_search, full_auto=not args.no_full_auto)
            if rc != 0:
                return rc
            if not args.no_validate:
                return run_validator(Path(output_file), categories, args.strict_warnings)
            return 0

        if args.mode == "batch":
            categories = args.categories.strip()
            if args.count <= 0:
                print("--count must be > 0")
                return 1
            if categories.lower() != "all" and not categories:
                print("--categories cannot be empty")
                return 1
            output_file = args.output.strip() or "question-pool.jsonl"
            prompt = build_batch_prompt(args.count, categories, output_file)
            rc = run_codex(prompt, search=not args.no_search, full_auto=not args.no_full_auto)
            if rc != 0:
                return rc
            if not args.no_validate:
                return run_validator(Path(output_file), categories, args.strict_warnings)
            return 0
    except FileNotFoundError as exc:
        print(str(exc))
        return 1

    print("Unknown mode")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
