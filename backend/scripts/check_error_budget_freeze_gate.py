#!/usr/bin/env python3
"""Release freeze gate checker driven by docs/sre/error-budget-status.json."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATUS_FILE = REPO_ROOT / "docs" / "sre" / "error-budget-status.json"
STATUS_FILE_ENV_KEY = "ERROR_BUDGET_STATUS_FILE"
HOTFIX_OVERRIDE_ENV_KEY = "RELEASE_GATE_HOTFIX_OVERRIDE"


def _parse_bool(raw: Any, *, default: bool = False) -> bool:
    if raw is None:
        return default
    normalized = str(raw).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _load_status_payload(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(f"status file not found: {path}") from exc
    except OSError as exc:
        raise RuntimeError(f"unable to read status file: {path}: {exc}") from exc

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"status file is not valid JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("status payload root must be an object")
    return payload


def evaluate_release_freeze(
    payload: dict[str, Any],
    *,
    hotfix_override: bool,
) -> tuple[bool, list[str], dict[str, Any]]:
    reasons: list[str] = []
    release_freeze = _parse_bool(payload.get("release_freeze"), default=False)
    checked_at = str(payload.get("checked_at") or "unknown")
    reason = payload.get("reason")

    if release_freeze:
        reasons.append("release_freeze_active")
        if hotfix_override:
            reasons.append("hotfix_override_enabled")
            return True, reasons, {
                "release_freeze": True,
                "checked_at": checked_at,
                "reason": reason,
                "override": True,
            }
        return False, reasons, {
            "release_freeze": True,
            "checked_at": checked_at,
            "reason": reason,
            "override": False,
        }

    return True, reasons, {
        "release_freeze": False,
        "checked_at": checked_at,
        "reason": reason,
        "override": False,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fail release gate when docs/sre/error-budget-status.json indicates release freeze."
        )
    )
    parser.add_argument(
        "--status-file",
        default=None,
        help=(
            "Path to error budget status JSON. Defaults to "
            f"${STATUS_FILE_ENV_KEY} or {DEFAULT_STATUS_FILE}."
        ),
    )
    parser.add_argument(
        "--allow-missing-status",
        action="store_true",
        help="Return success when status file is missing.",
    )
    parser.add_argument(
        "--hotfix-override-env",
        default=HOTFIX_OVERRIDE_ENV_KEY,
        help="Environment variable name used for temporary hotfix override.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    raw_status_path = (args.status_file or os.getenv(STATUS_FILE_ENV_KEY) or "").strip()
    status_path = Path(raw_status_path) if raw_status_path else DEFAULT_STATUS_FILE
    hotfix_override = _parse_bool(os.getenv(args.hotfix_override_env), default=False)

    print("[error-budget-freeze-gate] checking release freeze status")
    print(f"  status_file: {status_path}")
    print(f"  hotfix_override_env: {args.hotfix_override_env}")
    print(f"  hotfix_override: {'yes' if hotfix_override else 'no'}")

    try:
        payload = _load_status_payload(status_path)
    except RuntimeError as exc:
        if args.allow_missing_status and "not found" in str(exc):
            print("[error-budget-freeze-gate] skipped: missing status file")
            print(f"  detail: {exc}")
            return 0
        print("[error-budget-freeze-gate] fail: unable to load status")
        print(f"  detail: {exc}")
        return 1

    passed, reasons, meta = evaluate_release_freeze(payload, hotfix_override=hotfix_override)

    print(f"  release_freeze: {'yes' if meta.get('release_freeze') else 'no'}")
    print(f"  checked_at: {meta.get('checked_at', 'unknown')}")
    if meta.get("reason"):
        print(f"  reason: {meta.get('reason')}")

    if not passed:
        print("[error-budget-freeze-gate] result: fail")
        print("  reasons:")
        for reason in reasons:
            print(f"    - {reason}")
        return 1

    print("[error-budget-freeze-gate] result: pass")
    if reasons:
        print("  notes:")
        for reason in reasons:
            print(f"    - {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
