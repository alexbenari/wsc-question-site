#!/usr/bin/env python3
"""Regenerate question-pools.json from question-pool*.jsonl files in repo root."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_MANIFEST = "question-pools.json"
POOL_PREFIX = "question-pool"
POOL_SUFFIX = ".jsonl"
GENERAL_POOL = f"{POOL_PREFIX}{POOL_SUFFIX}"


def discover_pool_files(root: Path) -> list[str]:
    files = []
    for path in root.iterdir():
        if not path.is_file():
            continue
        name = path.name
        if not name.startswith(POOL_PREFIX) or not name.endswith(POOL_SUFFIX):
            continue
        files.append(name)

    files.sort()
    if GENERAL_POOL in files:
        files.remove(GENERAL_POOL)
        files.insert(0, GENERAL_POOL)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update question-pools.json using question-pool*.jsonl files found in repo root."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory to scan (default: current directory).",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_MANIFEST,
        help=f"Manifest file path relative to --root (default: {DEFAULT_MANIFEST}).",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR: root directory not found: {root}")
        return 1

    files = discover_pool_files(root)
    manifest_path = root / args.output
    payload = {"files": files}
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {manifest_path}")
    print(f"Discovered {len(files)} pool file(s).")
    for name in files:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
