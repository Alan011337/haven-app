#!/usr/bin/env python3
"""Fail when tracked duplicate suffix files (e.g. `name 2.ts`) exist."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
_DUPLICATE_SUFFIX_PATTERN = re.compile(r"(?:^|/)[^/]+ 2(?:\.[^/]+)?$")


def _tracked_files() -> list[str]:
    output = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        text=True,
        encoding="utf-8",
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def _untracked_files() -> list[str]:
    output = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--others", "--exclude-standard"],
        text=True,
        encoding="utf-8",
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def collect_violations(*, include_untracked: bool = True) -> list[str]:
    violations: list[str] = []
    candidates = _tracked_files()
    if include_untracked:
        candidates.extend(_untracked_files())
    seen: set[str] = set()
    for rel_path in candidates:
        if rel_path in seen:
            continue
        seen.add(rel_path)
        normalized = rel_path.replace("\\", "/")
        if not (REPO_ROOT / normalized).exists():
            # Deletions may be pending in a dirty worktree before staging.
            continue
        if _DUPLICATE_SUFFIX_PATTERN.search(normalized):
            violations.append(normalized)
    return sorted(violations)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help="Only scan tracked files. Default scans tracked + untracked files.",
    )
    args = parser.parse_args()
    violations = collect_violations(include_untracked=not args.tracked_only)
    if violations:
        print("[duplicate-suffix-files] fail")
        for violation in violations:
            print(f"- duplicate_suffix_file:{violation}")
        return 1
    print("[duplicate-suffix-files] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
