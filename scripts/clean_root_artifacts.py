#!/usr/bin/env python3
"""Remove generated / historical / temporary artifacts from the repository root.

Run with --dry-run to preview, then with --delete to remove.
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Patterns for obviously generated/historical files.
ARTIFACT_PATTERNS = [
    "*_run*.txt",
    "*_run*.out",
    "api_*.txt",
    "api_*.xml",
    "bandit*.txt",
    "bandit*.json",
    "bandit*.stdout",
    "bandit*.stderr",
    "coverage*.xml",
    "coverage*.json",
    "coverage*.html",
    "coverage_*.txt",
    "*.bak",
    "*.tmp",
    "*.log",
    "*phase*.txt",
    "*seq*.txt",
]

# Always keep files that are real config / source / docs.
KEEP_PATTERNS = [
    ".gitignore",
    ".env*",
    "requirements.txt",
    "README*",
    "CHANGELOG*",
    "LICENSE",
    "*.md",
    "*.py",
    "*.yaml",
    "*.yml",
    "*.json",
    "*.toml",
    "*.ini",
    "*.cfg",
    "*.lock",
]


def is_artifact(path: Path) -> bool:
    if any(fnmatch.fnmatch(path.name, kp) for kp in KEEP_PATTERNS):
        return False
    return any(fnmatch.fnmatch(path.name, pattern) for pattern in ARTIFACT_PATTERNS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean repository root artifacts")
    parser.add_argument("--delete", action="store_true", help="actually delete files")
    parser.add_argument("--root", type=Path, default=ROOT, help="repo root to clean")
    args = parser.parse_args()

    candidates = sorted(p for p in args.root.iterdir() if p.is_file() and is_artifact(p))
    if not candidates:
        print("No artifact candidates found in root.")
        return 0

    print(f"Found {len(candidates)} artifact(s) in {args.root}:")
    for p in candidates:
        print(f"  {p.name}")

    if args.delete:
        removed = 0
        for p in candidates:
            try:
                p.unlink()
                removed += 1
            except OSError as exc:
                print(f"  failed to delete {p.name}: {exc}", file=sys.stderr)
        print(f"Removed {removed} artifact(s).")
    else:
        print("Dry-run complete. Use --delete to remove the listed files.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
