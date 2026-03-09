#!/usr/bin/env python3
"""Validate release-gate hotfix override contract for CI/workflows."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

RELAXATION_FLAGS = (
    "RELEASE_GATE_ALLOW_MISSING_SLO_URL",
    "RELEASE_GATE_ALLOW_MISSING_LAUNCH_SIGNOFF",
    "RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE",
    "RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE",
)
HOTFIX_OVERRIDE_KEY = "RELEASE_GATE_HOTFIX_OVERRIDE"
OVERRIDE_REASON_KEY = "RELEASE_GATE_OVERRIDE_REASON"
OVERRIDE_REASON_PATTERN_KEY = "RELEASE_GATE_OVERRIDE_REASON_PATTERN"
DEFAULT_OVERRIDE_REASON_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{5,120}$"


def _parse_bool(name: str, raw: str | None, *, default: bool = False) -> tuple[bool, str | None]:
    if raw is None or str(raw).strip() == "":
        return default, None

    normalized = str(raw).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True, None
    if normalized in {"0", "false", "no", "off"}:
        return False, None
    return default, f"{name} must be one of: 1/0/true/false/yes/no/on/off"


def _write_summary(path: str | None, payload: dict[str, Any]) -> None:
    if not path:
        return
    try:
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print("[release-gate-override] warn: failed to write summary")
        print(f"  detail: {exc}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate release gate relaxations require explicit hotfix override contract."
    )
    parser.add_argument("--summary-path", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    summary_path = (args.summary_path or "").strip() or None

    invalid_flags: list[str] = []
    enabled_relaxations: list[str] = []
    for key in RELAXATION_FLAGS:
        value, issue = _parse_bool(key, os.getenv(key), default=False)
        if issue:
            invalid_flags.append(issue)
        if value:
            enabled_relaxations.append(key)

    hotfix_override, hotfix_issue = _parse_bool(
        HOTFIX_OVERRIDE_KEY,
        os.getenv(HOTFIX_OVERRIDE_KEY),
        default=False,
    )
    if hotfix_issue:
        invalid_flags.append(hotfix_issue)

    override_reason = (os.getenv(OVERRIDE_REASON_KEY) or "").strip()
    override_reason_safe = override_reason[:120]
    override_reason_pattern_raw = (
        os.getenv(OVERRIDE_REASON_PATTERN_KEY) or DEFAULT_OVERRIDE_REASON_PATTERN
    ).strip()

    try:
        override_reason_pattern = re.compile(override_reason_pattern_raw)
    except re.error:
        invalid_flags.append(f"{OVERRIDE_REASON_PATTERN_KEY} is not a valid regex")
        override_reason_pattern = re.compile(DEFAULT_OVERRIDE_REASON_PATTERN)

    if len(override_reason) > 300:
        invalid_flags.append(f"{OVERRIDE_REASON_KEY} is too long (max 300 chars)")

    mode = "override" if enabled_relaxations else "fail_closed"
    summary_payload = {
        "result": "pass",
        "mode": mode,
        "hotfix_override": hotfix_override,
        "override_reason_present": bool(override_reason),
        "override_reason": override_reason_safe,
        "override_reason_pattern": override_reason_pattern_raw,
        "enabled_relaxations": enabled_relaxations,
        "reasons": [],
    }

    print("[release-gate-override] checking contract")
    print(f"  mode: {mode}")
    print(f"  hotfix_override: {'enabled' if hotfix_override else 'disabled'}")
    print(f"  override_reason_present: {'yes' if override_reason else 'no'}")
    print(f"  override_reason: {override_reason_safe or 'none'}")
    print(
        "  enabled_relaxations: "
        + (", ".join(enabled_relaxations) if enabled_relaxations else "none")
    )

    if invalid_flags:
        print("[release-gate-override] result: fail")
        print("  reasons:")
        for issue in invalid_flags:
            print(f"    - {issue}")
        summary_payload["result"] = "fail"
        summary_payload["reasons"] = invalid_flags
        _write_summary(summary_path, summary_payload)
        return 1

    if enabled_relaxations:
        reasons: list[str] = []
        if not hotfix_override:
            reasons.append("gate_relaxations_require_hotfix_override")
        if not override_reason:
            reasons.append("gate_relaxations_require_override_reason")
        elif not override_reason_pattern.fullmatch(override_reason):
            reasons.append("gate_relaxations_require_ticket_like_override_reason")

        if reasons:
            print("[release-gate-override] result: fail")
            print("  reasons:")
            for reason in reasons:
                print(f"    - {reason}")
            summary_payload["result"] = "fail"
            summary_payload["reasons"] = reasons
            _write_summary(summary_path, summary_payload)
            return 1

    print("[release-gate-override] result: pass")
    _write_summary(summary_path, summary_payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
