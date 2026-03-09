#!/usr/bin/env python3
"""Service-tier-aware error budget release gate."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_FILE = REPO_ROOT / "docs" / "sre" / "service-tiering.json"
DEFAULT_STATUS_FILE = REPO_ROOT / "docs" / "sre" / "error-budget-status.json"

POLICY_FILE_ENV_KEY = "SERVICE_TIER_POLICY_FILE"
STATUS_FILE_ENV_KEY = "ERROR_BUDGET_STATUS_FILE"
TARGET_TIER_ENV_KEY = "RELEASE_TARGET_TIER"
RELEASE_INTENT_ENV_KEY = "RELEASE_INTENT"
HOTFIX_OVERRIDE_ENV_KEY = "RELEASE_GATE_HOTFIX_OVERRIDE"

VALID_RELEASE_INTENTS = {"feature", "bugfix", "security", "hotfix"}


def _parse_bool(raw: Any, *, default: bool = False) -> bool:
    if raw is None:
        return default
    normalized = str(raw).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(f"{label} not found: {path}") from exc
    except OSError as exc:
        raise RuntimeError(f"unable to read {label}: {path}: {exc}") from exc

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} is not valid JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} root must be an object")
    return payload


def _validate_release_intent(raw_intent: str) -> str:
    normalized = raw_intent.strip().lower()
    if normalized not in VALID_RELEASE_INTENTS:
        valid_sorted = ", ".join(sorted(VALID_RELEASE_INTENTS))
        raise RuntimeError(
            f"{RELEASE_INTENT_ENV_KEY} must be one of: {valid_sorted} (got `{raw_intent}`)"
        )
    return normalized


def _load_target_tier(*, policy: dict[str, Any], raw_target_tier: str | None) -> str:
    tiers = policy.get("tiers")
    if not isinstance(tiers, dict) or not tiers:
        raise RuntimeError("service-tier policy missing non-empty `tiers` object")

    target = (raw_target_tier or "").strip()
    if not target:
        target = str(policy.get("default_target_tier") or "").strip()
    if not target:
        raise RuntimeError("service-tier policy missing `default_target_tier`")
    if target not in tiers:
        available = ", ".join(sorted(tiers.keys()))
        raise RuntimeError(f"target tier `{target}` not found in policy tiers ({available})")
    return target


def evaluate_service_tier_gate(
    *,
    policy: dict[str, Any],
    status_payload: dict[str, Any],
    target_tier: str,
    release_intent: str,
    hotfix_override: bool,
) -> tuple[bool, list[str], dict[str, Any]]:
    reasons: list[str] = []

    tiers = policy.get("tiers")
    assert isinstance(tiers, dict)
    tier_payload = tiers.get(target_tier)
    if not isinstance(tier_payload, dict):
        raise RuntimeError(f"tier payload for `{target_tier}` must be object")

    freeze_enforced = _parse_bool(tier_payload.get("error_budget_freeze_enforced"), default=True)
    allowed_when_frozen_raw = tier_payload.get("allowed_release_intents_when_frozen")
    if isinstance(allowed_when_frozen_raw, list):
        allowed_when_frozen = {
            str(item).strip().lower()
            for item in allowed_when_frozen_raw
            if str(item).strip()
        }
    else:
        allowed_when_frozen = {"bugfix", "security", "hotfix"}
    allowed_when_frozen = {
        intent for intent in allowed_when_frozen if intent in VALID_RELEASE_INTENTS
    }
    if not allowed_when_frozen:
        allowed_when_frozen = {"bugfix", "security", "hotfix"}

    release_freeze = _parse_bool(status_payload.get("release_freeze"), default=False)
    checked_at = str(status_payload.get("checked_at") or "unknown")
    freeze_reason = status_payload.get("reason")

    meta = {
        "target_tier": target_tier,
        "release_intent": release_intent,
        "release_freeze": release_freeze,
        "tier_display_name": str(tier_payload.get("display_name") or target_tier),
        "tier_error_budget_freeze_enforced": freeze_enforced,
        "allowed_release_intents_when_frozen": sorted(allowed_when_frozen),
        "checked_at": checked_at,
        "freeze_reason": freeze_reason,
        "hotfix_override": hotfix_override,
    }

    if not release_freeze:
        return True, reasons, meta

    if release_intent in allowed_when_frozen:
        reasons.append("release_intent_allowed_during_freeze")
        return True, reasons, meta

    if hotfix_override and release_intent in {"hotfix", "security", "bugfix"}:
        reasons.append("hotfix_override_enabled")
        return True, reasons, meta

    if freeze_enforced:
        reasons.append("tier_error_budget_freeze_active")
        return False, reasons, meta

    reasons.append("tier_freeze_policy_not_enforced")
    return True, reasons, meta


def _write_summary(path: str | None, payload: dict[str, Any]) -> None:
    if not path:
        return
    try:
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print("[service-tier-gate] warn: failed to write summary")
        print(f"  detail: {exc}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Service-tier-aware release freeze gate. "
            "Tier-0 is blocked by error budget freeze; Tier-1 policy is configurable."
        )
    )
    parser.add_argument(
        "--policy-file",
        default=None,
        help=f"Path to service-tier policy JSON (default: ${POLICY_FILE_ENV_KEY} or {DEFAULT_POLICY_FILE}).",
    )
    parser.add_argument(
        "--status-file",
        default=None,
        help=f"Path to error budget status JSON (default: ${STATUS_FILE_ENV_KEY} or {DEFAULT_STATUS_FILE}).",
    )
    parser.add_argument(
        "--target-tier",
        default=None,
        help=f"Release target tier (default: ${TARGET_TIER_ENV_KEY} or policy default).",
    )
    parser.add_argument(
        "--release-intent",
        default=None,
        help=(
            f"Release intent (feature/bugfix/security/hotfix). "
            f"Defaults to ${RELEASE_INTENT_ENV_KEY} or `feature`."
        ),
    )
    parser.add_argument(
        "--allow-missing-status",
        action="store_true",
        help="Return success when status file is missing (PR/local dry-run).",
    )
    parser.add_argument(
        "--summary-path",
        default=None,
        help="Optional summary JSON output path for CI step summaries.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    summary_path = (args.summary_path or "").strip() or None
    policy_file_raw = (args.policy_file or os.getenv(POLICY_FILE_ENV_KEY) or "").strip()
    status_file_raw = (args.status_file or os.getenv(STATUS_FILE_ENV_KEY) or "").strip()
    policy_path = Path(policy_file_raw) if policy_file_raw else DEFAULT_POLICY_FILE
    status_path = Path(status_file_raw) if status_file_raw else DEFAULT_STATUS_FILE

    try:
        policy = _load_json_object(policy_path, label="service-tier policy")
    except RuntimeError as exc:
        print("[service-tier-gate] fail: unable to load policy")
        print(f"  detail: {exc}")
        _write_summary(
            summary_path,
            {
                "result": "fail",
                "reasons": ["policy_load_error"],
                "meta": {"detail": str(exc)},
            },
        )
        return 1

    try:
        target_tier = _load_target_tier(
            policy=policy,
            raw_target_tier=(args.target_tier or os.getenv(TARGET_TIER_ENV_KEY)),
        )
        release_intent = _validate_release_intent(
            args.release_intent or os.getenv(RELEASE_INTENT_ENV_KEY, "feature")
        )
    except RuntimeError as exc:
        print("[service-tier-gate] fail: invalid gate configuration")
        print(f"  detail: {exc}")
        _write_summary(
            summary_path,
            {
                "result": "fail",
                "reasons": ["invalid_gate_configuration"],
                "meta": {"detail": str(exc)},
            },
        )
        return 1

    hotfix_override = _parse_bool(os.getenv(HOTFIX_OVERRIDE_ENV_KEY), default=False)

    print("[service-tier-gate] checking service-tier error budget policy")
    print(f"  policy_file: {policy_path}")
    print(f"  status_file: {status_path}")
    print(f"  target_tier: {target_tier}")
    print(f"  release_intent: {release_intent}")
    print(f"  hotfix_override: {'yes' if hotfix_override else 'no'}")

    try:
        status_payload = _load_json_object(status_path, label="error budget status")
    except RuntimeError as exc:
        if args.allow_missing_status and "not found" in str(exc):
            print("[service-tier-gate] skipped: missing status file")
            print(f"  detail: {exc}")
            _write_summary(
                summary_path,
                {
                    "result": "pass",
                    "reasons": ["status_file_missing_allowed"],
                    "meta": {
                        "target_tier": target_tier,
                        "release_intent": release_intent,
                        "status_file": str(status_path),
                        "hotfix_override": hotfix_override,
                    },
                },
            )
            return 0
        print("[service-tier-gate] fail: unable to load status file")
        print(f"  detail: {exc}")
        _write_summary(
            summary_path,
            {
                "result": "fail",
                "reasons": ["status_load_error"],
                "meta": {
                    "target_tier": target_tier,
                    "release_intent": release_intent,
                    "detail": str(exc),
                },
            },
        )
        return 1

    passed, reasons, meta = evaluate_service_tier_gate(
        policy=policy,
        status_payload=status_payload,
        target_tier=target_tier,
        release_intent=release_intent,
        hotfix_override=hotfix_override,
    )
    print(f"  release_freeze: {'yes' if meta.get('release_freeze') else 'no'}")
    print(
        "  tier_error_budget_freeze_enforced: "
        + ("yes" if meta.get("tier_error_budget_freeze_enforced") else "no")
    )

    if not passed:
        print("[service-tier-gate] result: fail")
        for reason in reasons:
            print(f"  - {reason}")
        _write_summary(
            summary_path,
            {
                "result": "fail",
                "reasons": reasons,
                "meta": meta,
            },
        )
        return 1

    print("[service-tier-gate] result: pass")
    if reasons:
        print("  notes:")
        for reason in reasons:
            print(f"    - {reason}")
    _write_summary(
        summary_path,
        {
            "result": "pass",
            "reasons": reasons,
            "meta": meta,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
