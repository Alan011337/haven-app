#!/usr/bin/env python3
"""Ensure frontend Next.js config exposes baseline security headers."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
NEXT_CONFIG_PATH = REPO_ROOT / "frontend" / "next.config.ts"

REQUIRED_MARKERS = [
    "async headers()",
    "source: '/:path*'",
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "Referrer-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Permissions-Policy",
]


def collect_violations() -> list[str]:
    if not NEXT_CONFIG_PATH.exists():
        return ["missing_frontend_next_config"]
    text = NEXT_CONFIG_PATH.read_text(encoding="utf-8")
    violations: list[str] = []
    for marker in REQUIRED_MARKERS:
        if marker not in text:
            violations.append(f"missing_marker:{marker}")
    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print("[frontend-security-headers-contract] fail")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("[frontend-security-headers-contract] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
