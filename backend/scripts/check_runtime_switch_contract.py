#!/usr/bin/env python3
"""Contract checks for centralized runtime feature switch usage."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SWITCH_PATH = REPO_ROOT / "backend" / "app" / "core" / "runtime_switches.py"
FEATURE_FLAGS_PATH = REPO_ROOT / "backend" / "app" / "services" / "feature_flags.py"


def collect_violations() -> list[str]:
    violations: list[str] = []
    if not RUNTIME_SWITCH_PATH.exists():
        violations.append("missing_runtime_switches_module")
    else:
        text = RUNTIME_SWITCH_PATH.read_text(encoding="utf-8")
        required_markers = (
            "class RuntimeFeatureSwitches",
            "get_runtime_feature_switches",
            "websocket_enabled",
            "email_notifications_enabled",
            "timeline_cursor_enabled",
        )
        for marker in required_markers:
            if marker not in text:
                violations.append(f"runtime_switches_missing_marker:{marker}")

    if not FEATURE_FLAGS_PATH.exists():
        violations.append("missing_feature_flags_module")
    else:
        ff_text = FEATURE_FLAGS_PATH.read_text(encoding="utf-8")
        if "get_runtime_feature_switches" not in ff_text:
            violations.append("feature_flags_not_using_runtime_switches")

    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print("[runtime-switch-contract] fail")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("[runtime-switch-contract] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
