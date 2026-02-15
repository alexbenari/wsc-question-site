#!/usr/bin/env python3
"""Validate WSC question-pool JSONL against schema + project guideline checks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


CATEGORY_SET = {
    "single_topic_understanding",
    "context_clues",
    "comparative_consequences",
    "thematic_synthesis",
}
CORRECT_SET = {"A", "B", "C", "D", "E"}
ABSOLUTE_TERMS = {
    "always",
    "never",
    "all",
    "none",
    "completely",
    "entirely",
    "impossible",
    "everyone",
    "nobody",
}
ID_PATTERN = re.compile(r"^q_[A-Za-z0-9]{6,22}$")


def words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9]+(?:['’\-][A-Za-z0-9]+)?", text)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]+", " ", text.lower())).strip()


def is_negative_question(question: str) -> bool:
    return bool(
        re.search(
            r"\b(not|except|least likely|isn['’]t|aren['’]t|doesn['’]t|cannot|can['’]t|never|false)\b",
            question.lower(),
        )
    )


def looks_one_sentence(question: str) -> bool:
    parts = [p.strip() for p in re.split(r"[.!?]+", question) if p.strip()]
    return len(parts) <= 1


def validate_shape(obj: dict) -> List[str]:
    errs: List[str] = []
    required = {"id", "category", "question", "choices", "correct", "topics"}
    missing = required - set(obj.keys())
    extra = set(obj.keys()) - required
    if missing:
        errs.append(f"missing required keys: {sorted(missing)}")
    if extra:
        errs.append(f"unexpected keys: {sorted(extra)}")
    if errs:
        return errs

    if not isinstance(obj["id"], str) or not ID_PATTERN.match(obj["id"]):
        errs.append("id must match pattern ^q_[A-Za-z0-9]{6,22}$")
    if obj["category"] not in CATEGORY_SET:
        errs.append(f"invalid category: {obj['category']}")
    if not isinstance(obj["question"], str) or not obj["question"].strip():
        errs.append("question must be non-empty string")
    if not isinstance(obj["choices"], list) or len(obj["choices"]) != 5:
        errs.append("choices must be array of exactly 5 strings")
    else:
        for i, c in enumerate(obj["choices"]):
            if not isinstance(c, str) or not c.strip():
                errs.append(f"choice {i+1} must be non-empty string")
    if obj["correct"] not in CORRECT_SET:
        errs.append(f"correct must be one of {sorted(CORRECT_SET)}")
    if not isinstance(obj["topics"], list) or len(obj["topics"]) < 1:
        errs.append("topics must be non-empty array of strings")
    else:
        for i, t in enumerate(obj["topics"]):
            if not isinstance(t, str) or not t.strip():
                errs.append(f"topic {i+1} must be non-empty string")
    return errs


def build_topic_evidence(topics_dir: Path) -> Dict[str, dict]:
    by_title: Dict[str, dict] = {}
    for topic_file in topics_dir.glob("*/topic.json"):
        try:
            data = json.loads(topic_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        title = str(data.get("title", "")).strip()
        if not title:
            continue
        artworks = data.get("artworks", [])
        persons = data.get("persons", [])
        artwork_terms = set()
        person_terms = set()
        for art in artworks:
            if isinstance(art, dict):
                title_term = str(art.get("title", "")).strip()
                creator_term = str(art.get("creator", "")).strip()
                if title_term:
                    artwork_terms.add(normalize(title_term))
                if creator_term:
                    artwork_terms.add(normalize(creator_term))
                    person_terms.add(normalize(creator_term))
        for p in persons:
            if isinstance(p, str) and p.strip():
                person_terms.add(normalize(p))
        by_title[title] = {
            "artwork_terms": {t for t in artwork_terms if t},
            "person_terms": {t for t in person_terms if t},
        }
    return by_title


def detect_artwork_or_person(obj: dict, topic_evidence: Dict[str, dict]) -> Tuple[bool, bool]:
    text = normalize(" ".join([obj["question"]] + obj["choices"]))

    artwork_terms = set()
    person_terms = set()
    for t in obj["topics"]:
        ev = topic_evidence.get(t)
        if ev:
            artwork_terms |= ev["artwork_terms"]
            person_terms |= ev["person_terms"]
    if not artwork_terms and not person_terms:
        for ev in topic_evidence.values():
            artwork_terms |= ev["artwork_terms"]
            person_terms |= ev["person_terms"]

    is_artwork = any(term and term in text for term in artwork_terms)
    is_person = any(term and term in text for term in person_terms)
    return is_artwork, is_person


def validate_question(
    obj: dict,
    idx: int,
    topic_evidence: Dict[str, dict],
    known_titles: set,
) -> Tuple[List[str], List[str], bool, bool, bool]:
    errs: List[str] = []
    warns: List[str] = []

    shape_errs = validate_shape(obj)
    if shape_errs:
        return [f"line {idx}: {e}" for e in shape_errs], warns, False, False, False

    q = obj["question"].strip()
    q_words = len(words(q))
    if q_words > 22:
        errs.append(f"line {idx}: question exceeds 22 words ({q_words})")
    if not looks_one_sentence(q):
        errs.append(f"line {idx}: question appears to contain multiple sentences")

    choices = obj["choices"]
    norm_choices = [normalize(c) for c in choices]
    if len(set(norm_choices)) != len(norm_choices):
        errs.append(f"line {idx}: choices contain duplicate/near-duplicate options")

    correct_idx = ord(obj["correct"]) - ord("A")
    correct_words = len(words(choices[correct_idx]))
    for i, choice in enumerate(choices):
        if i == correct_idx:
            continue
        if correct_words > len(words(choice)) + 1:
            errs.append(
                f"line {idx}: correct answer too long vs distractor {chr(ord('A') + i)} "
                f"({correct_words} vs {len(words(choice))})"
            )
            break

    for c in choices:
        lower = c.lower()
        if any(re.search(rf"\b{re.escape(term)}\b", lower) for term in ABSOLUTE_TERMS):
            warns.append(f"line {idx}: possible trivial distractor/absolute wording: '{c}'")
            break

    cat = obj["category"]
    tlen = len(obj["topics"])
    if cat in {"comparative_consequences", "thematic_synthesis"} and tlen != 2:
        errs.append(f"line {idx}: {cat} must have exactly 2 topics (found {tlen})")
    if cat in {"single_topic_understanding", "context_clues"} and tlen != 1:
        warns.append(f"line {idx}: {cat} usually should have exactly 1 topic (found {tlen})")

    for t in obj["topics"]:
        if t not in known_titles:
            warns.append(f"line {idx}: topic not found in topics dir: '{t}'")

    neg = is_negative_question(q)
    is_artwork, is_person = detect_artwork_or_person(obj, topic_evidence)
    return errs, warns, neg, is_artwork, is_person


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate WSC question pool.")
    parser.add_argument("--input", required=True, help="Path to question JSONL file.")
    parser.add_argument("--topics-dir", default="topics", help="Path to topics directory.")
    parser.add_argument("--strict-warnings", action="store_true", help="Treat warnings as errors.")
    parser.add_argument(
        "--allowed-categories",
        default="all",
        help="Comma-separated allowed categories, or 'all' (default).",
    )
    parser.add_argument(
        "--check-category-balance",
        action="store_true",
        help="Require roughly equal counts across allowed categories.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    topics_dir = Path(args.topics_dir)
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}")
        return 1
    if not topics_dir.exists():
        print(f"ERROR: topics dir not found: {topics_dir}")
        return 1

    topic_evidence = build_topic_evidence(topics_dir)
    known_titles = set(topic_evidence.keys())
    if not known_titles:
        print("ERROR: no topic.json files found under topics dir.")
        return 1

    allowed_categories = CATEGORY_SET
    if args.allowed_categories.strip().lower() != "all":
        requested = {c.strip() for c in args.allowed_categories.split(",") if c.strip()}
        unknown = requested - CATEGORY_SET
        if unknown:
            print(f"ERROR: unknown categories in --allowed-categories: {sorted(unknown)}")
            return 1
        allowed_categories = requested

    errors: List[str] = []
    warnings: List[str] = []
    total = 0
    neg_count = 0
    artwork_count = 0
    person_count = 0
    category_counts = {c: 0 for c in CATEGORY_SET}
    correct_letter_counts = {k: 0 for k in sorted(CORRECT_SET)}
    correct_sequence: List[str] = []
    seen_ids = set()

    with input_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            total += 1
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"line {i}: invalid JSON: {exc}")
                continue
            e, w, neg, art, person = validate_question(obj, i, topic_evidence, known_titles)
            errors.extend(e)
            warnings.extend(w)
            if not e:
                qid = obj["id"]
                if qid in seen_ids:
                    errors.append(f"line {i}: duplicate id '{qid}'")
                    continue
                seen_ids.add(qid)
                if obj["category"] not in allowed_categories:
                    errors.append(
                        f"line {i}: category '{obj['category']}' not allowed by --allowed-categories"
                    )
                category_counts[obj["category"]] += 1
                neg_count += 1 if neg else 0
                artwork_count += 1 if art else 0
                person_count += 1 if person else 0
                correct_letter_counts[obj["correct"]] += 1
                correct_sequence.append(obj["correct"])

    if total == 0:
        errors.append("no JSONL records found")

    if total > 0:
        neg_ratio = neg_count / total
        art_ratio = artwork_count / total
        person_ratio = person_count / total
        if neg_ratio < 0.30:
            errors.append(f"negative-phrased ratio below 30% ({neg_ratio:.1%})")
        if art_ratio < 0.20:
            errors.append(f"artwork-related ratio below 20% ({art_ratio:.1%})")
        if person_ratio < 0.20:
            errors.append(f"person-related ratio below 20% ({person_ratio:.1%})")

        print(f"Total questions: {total}")
        print("Category counts:")
        for c in sorted(category_counts.keys()):
            print(f"  - {c}: {category_counts[c]}")
        print(f"Negative phrasing: {neg_count}/{total} ({neg_count/total:.1%})")
        print(f"Artwork-related: {artwork_count}/{total} ({artwork_count/total:.1%})")
        print(f"Person-related: {person_count}/{total} ({person_count/total:.1%})")
        print("Correct-letter distribution:")
        for k in sorted(correct_letter_counts.keys()):
            print(f"  - {k}: {correct_letter_counts[k]}")

        # Random placement checks (heuristic)
        # 1) Distribution should not be heavily skewed.
        for letter, count in correct_letter_counts.items():
            ratio = count / total
            if ratio < 0.10 or ratio > 0.35:
                errors.append(
                    f"correct-answer placement skewed: {letter} ratio {ratio:.1%} outside [10%, 35%]"
                )

        # 2) Avoid long repeated runs of same letter.
        max_run = 1
        cur_run = 1
        for i in range(1, len(correct_sequence)):
            if correct_sequence[i] == correct_sequence[i - 1]:
                cur_run += 1
                if cur_run > max_run:
                    max_run = cur_run
            else:
                cur_run = 1
        if max_run >= 5:
            errors.append(f"correct-answer placement has long repeated run (max run = {max_run})")

        # 3) Category balance check (optional)
        if args.check_category_balance and allowed_categories:
            active_counts = [category_counts[c] for c in sorted(allowed_categories)]
            min_c = min(active_counts)
            max_c = max(active_counts)
            if min_c == 0:
                errors.append("category balance check failed: at least one allowed category has zero items")
            else:
                ratio = max_c / min_c
                if ratio > 1.25:
                    errors.append(
                        f"category balance check failed: max/min ratio {ratio:.2f} exceeds 1.25"
                    )

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings[:100]:
            print(f"  - {w}")
        if len(warnings) > 100:
            print(f"  ... {len(warnings) - 100} more warnings")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors[:200]:
            print(f"  - {e}")
        if len(errors) > 200:
            print(f"  ... {len(errors) - 200} more errors")
        return 1

    if args.strict_warnings and warnings:
        print("\nValidation failed due to strict warnings mode.")
        return 1

    print("\nValidation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
