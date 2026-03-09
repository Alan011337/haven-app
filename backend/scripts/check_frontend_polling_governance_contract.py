#!/usr/bin/env python3
"""Ensure frontend polling uses centralized adaptive polling policy."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POLLING_POLICY_PATH = REPO_ROOT / "frontend" / "src" / "lib" / "polling-policy.ts"
ADAPTIVE_POLLING_PATH = REPO_ROOT / "frontend" / "src" / "lib" / "adaptive-polling.ts"
REALTIME_POLICY_PATH = REPO_ROOT / "frontend" / "src" / "lib" / "realtime-policy.ts"
SOCKET_HOOK_PATH = REPO_ROOT / "frontend" / "src" / "hooks" / "useSocket.ts"
REQUIRED_IMPORT_FILES = [
    REPO_ROOT / "frontend" / "src" / "features" / "notifications" / "useNotificationsData.ts",
    REPO_ROOT / "frontend" / "src" / "features" / "home" / "useHomeData.ts",
    REPO_ROOT / "frontend" / "src" / "components" / "layout" / "Sidebar.tsx",
    REPO_ROOT / "frontend" / "src" / "components" / "system" / "DegradationBanner.tsx",
    REPO_ROOT / "frontend" / "src" / "components" / "features" / "DailyCard.tsx",
]


def collect_violations() -> list[str]:
    violations: list[str] = []
    if not POLLING_POLICY_PATH.exists():
        violations.append("missing_polling_policy_module")
    else:
        policy_text = POLLING_POLICY_PATH.read_text(encoding="utf-8")
        for marker in ("getAdaptiveIntervalMs", "buildAdaptiveRefetchInterval"):
            if marker not in policy_text:
                violations.append(f"polling_policy_missing_marker:{marker}")

    if not ADAPTIVE_POLLING_PATH.exists():
        violations.append("missing_adaptive_polling_module")
    else:
        adaptive_text = ADAPTIVE_POLLING_PATH.read_text(encoding="utf-8")
        if "startAdaptivePolling" not in adaptive_text:
            violations.append("adaptive_polling_missing_marker:startAdaptivePolling")

    if not REALTIME_POLICY_PATH.exists():
        violations.append("missing_realtime_policy_module")
    else:
        realtime_text = REALTIME_POLICY_PATH.read_text(encoding="utf-8")
        for marker in ("REALTIME_FALLBACK_EVENT", "emitRealtimeFallback"):
            if marker not in realtime_text:
                violations.append(f"realtime_policy_missing_marker:{marker}")

    if not SOCKET_HOOK_PATH.exists():
        violations.append(f"missing_required_file:{SOCKET_HOOK_PATH.relative_to(REPO_ROOT)}")
    else:
        socket_text = SOCKET_HOOK_PATH.read_text(encoding="utf-8")
        if "emitRealtimeFallback" not in socket_text:
            violations.append("socket_hook_missing_realtime_policy_usage")

    for file_path in REQUIRED_IMPORT_FILES:
        if not file_path.exists():
            violations.append(f"missing_required_file:{file_path.relative_to(REPO_ROOT)}")
            continue
        text = file_path.read_text(encoding="utf-8")
        if "polling-policy" not in text and "adaptive-polling" not in text:
            violations.append(f"polling_policy_not_used:{file_path.relative_to(REPO_ROOT)}")

    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print("[frontend-polling-governance-contract] fail")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("[frontend-polling-governance-contract] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
