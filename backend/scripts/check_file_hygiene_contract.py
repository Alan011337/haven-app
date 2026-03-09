#!/usr/bin/env python3
"""Fail on accidental duplicate/temporary file naming patterns in repo."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BLOCKED_SUFFIXES = (" 2.py", " 2.ts", " 2.tsx", " copy.py", " copy.ts", " copy.tsx")
BLOCKED_PATTERNS = ("~", ".bak", ".old")
SCANNED_ROOTS = (
    REPO_ROOT / "backend" / "app",
    REPO_ROOT / "backend" / "tests",
    REPO_ROOT / "backend" / "scripts",
    REPO_ROOT / "frontend" / "src",
    REPO_ROOT / "frontend" / "e2e",
    REPO_ROOT / "scripts",
    REPO_ROOT / "docs",
    REPO_ROOT / ".github" / "workflows",
)


def collect_violations() -> list[str]:
    violations: list[str] = []
    for root in SCANNED_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(REPO_ROOT)
            rel_text = str(rel)
            if any(part in {"node_modules", "venv", "venv312", ".venv-gate", "__pycache__", ".next"} for part in rel.parts):
                continue
            if rel.name.endswith(BLOCKED_SUFFIXES):
                violations.append(f"blocked_duplicate_suffix:{rel_text}")
            if rel.name.endswith(BLOCKED_PATTERNS):
                violations.append(f"blocked_temp_suffix:{rel_text}")
            if "  " in rel.name:
                violations.append(f"blocked_double_space:{rel_text}")
    return sorted(set(violations))


def main() -> int:
    violations = collect_violations()
    if violations:
        print("[file-hygiene-contract] fail")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("[file-hygiene-contract] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
