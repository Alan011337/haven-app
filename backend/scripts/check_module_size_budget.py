#!/usr/bin/env python3
"""Fail-closed guardrail for oversized core modules."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

MODULE_LINE_BUDGETS: dict[Path, int] = {
    REPO_ROOT / "backend" / "app" / "services" / "ai_router.py": 1900,
    REPO_ROOT / "backend" / "app" / "services" / "ai.py": 980,
    REPO_ROOT / "backend" / "app" / "services" / "notification.py": 820,
    REPO_ROOT / "backend" / "app" / "services" / "notification_outbox.py": 940,
    REPO_ROOT / "backend" / "app" / "core" / "health_routes.py": 940,
    REPO_ROOT / "backend" / "app" / "api" / "routers" / "card_decks.py": 980,
    REPO_ROOT / "frontend" / "src" / "services" / "api-client.ts": 730,
    REPO_ROOT / "frontend" / "src" / "components" / "features" / "DailyCard.tsx": 650,
    REPO_ROOT / "frontend" / "src" / "hooks" / "useSocket.ts": 360,
    REPO_ROOT / "frontend" / "src" / "features" / "home" / "useHomeData.ts": 460,
}


def _count_lines(path: Path) -> int:
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def collect_violations() -> list[str]:
    violations: list[str] = []
    for path, budget in MODULE_LINE_BUDGETS.items():
        if not path.exists():
            violations.append(f"missing_module:{path.relative_to(REPO_ROOT)}")
            continue
        line_count = _count_lines(path)
        if line_count > budget:
            violations.append(
                f"module_over_budget:{path.relative_to(REPO_ROOT)}:{line_count}>{budget}"
            )
    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print("[module-size-budget] fail")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("[module-size-budget] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
