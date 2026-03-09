#!/usr/bin/env python3
"""Policy-as-code check for API inventory owner attestation freshness."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

ATTESTATION_SCHEMA_VERSION = "1.0.0"
ATTESTATION_ARTIFACT_KIND = "api-inventory-owner-attestation"
DEFAULT_MAX_AGE_DAYS = 90
DEFAULT_MIN_REMAINING_DAYS = 14
MAX_FUTURE_SKEW_SECONDS = 300

ATTESTATION_PATH = REPO_ROOT / "docs" / "security" / "api-inventory-owner-attestation.json"
INVENTORY_PATH = REPO_ROOT / "docs" / "security" / "api-inventory.json"
CODEOWNERS_PATH = REPO_ROOT / ".github" / "CODEOWNERS"


@dataclass(frozen=True)
class OwnerAttestationViolation:
    owner_team: str
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_iso8601(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _resolve_max_age_days(attestation_payload: dict[str, Any]) -> tuple[int | None, str | None]:
    override = os.getenv("API_INVENTORY_ATTESTATION_MAX_AGE_DAYS")
    if override is not None and override.strip() != "":
        try:
            value = int(override)
        except ValueError:
            return None, "env API_INVENTORY_ATTESTATION_MAX_AGE_DAYS must be an integer"
        if value <= 0:
            return None, "env API_INVENTORY_ATTESTATION_MAX_AGE_DAYS must be > 0"
        return value, None

    configured = attestation_payload.get("max_attestation_age_days")
    if configured is None:
        return DEFAULT_MAX_AGE_DAYS, None

    if not isinstance(configured, int) or configured <= 0:
        return None, "max_attestation_age_days must be a positive integer"

    return configured, None


def _resolve_min_remaining_days(
    attestation_payload: dict[str, Any],
) -> tuple[int | None, str | None]:
    override = os.getenv("API_INVENTORY_ATTESTATION_MIN_DAYS_REMAINING")
    if override is not None and override.strip() != "":
        try:
            value = int(override)
        except ValueError:
            return (
                None,
                "env API_INVENTORY_ATTESTATION_MIN_DAYS_REMAINING must be an integer",
            )
        if value < 0:
            return (
                None,
                "env API_INVENTORY_ATTESTATION_MIN_DAYS_REMAINING must be >= 0",
            )
        return value, None

    configured = attestation_payload.get("min_attestation_days_remaining")
    if configured is None:
        return DEFAULT_MIN_REMAINING_DAYS, None

    if not isinstance(configured, int) or configured < 0:
        return None, "min_attestation_days_remaining must be a non-negative integer"

    return configured, None


def _inventory_owner_teams(inventory_payload: dict[str, Any]) -> set[str]:
    teams: set[str] = set()
    for entry in inventory_payload.get("entries", []):
        if not isinstance(entry, dict):
            continue
        team = str(entry.get("owner_team", "")).strip()
        if team:
            teams.add(team)
    return teams


def _load_codeowners_patterns(path: Path = CODEOWNERS_PATH) -> set[str]:
    if not path.exists():
        return set()

    patterns: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        token = stripped.split()[0]
        if token:
            patterns.add(token)
    return patterns


def collect_owner_attestation_violations(
    *,
    attestation_payload: dict[str, Any] | None = None,
    inventory_payload: dict[str, Any] | None = None,
    now_utc: datetime | None = None,
    codeowners_patterns: set[str] | None = None,
) -> list[OwnerAttestationViolation]:
    payload = attestation_payload if attestation_payload is not None else _load_json(ATTESTATION_PATH)
    inventory = inventory_payload if inventory_payload is not None else _load_json(INVENTORY_PATH)
    now = now_utc.astimezone(timezone.utc) if now_utc is not None else datetime.now(timezone.utc)
    codeowner_refs = _load_codeowners_patterns() if codeowners_patterns is None else codeowners_patterns

    violations: list[OwnerAttestationViolation] = []

    schema_version = payload.get("schema_version")
    if schema_version != ATTESTATION_SCHEMA_VERSION:
        violations.append(
            OwnerAttestationViolation(
                owner_team="*",
                reason="invalid_schema_version",
                details=(
                    f"schema_version must be `{ATTESTATION_SCHEMA_VERSION}` "
                    f"(got `{schema_version}`)."
                ),
            )
        )

    artifact_kind = payload.get("artifact_kind")
    if artifact_kind != ATTESTATION_ARTIFACT_KIND:
        violations.append(
            OwnerAttestationViolation(
                owner_team="*",
                reason="invalid_artifact_kind",
                details=(
                    f"artifact_kind must be `{ATTESTATION_ARTIFACT_KIND}` "
                    f"(got `{artifact_kind}`)."
                ),
            )
        )

    updated_at = _parse_iso8601(payload.get("updated_at"))
    if updated_at is None:
        violations.append(
            OwnerAttestationViolation(
                owner_team="*",
                reason="invalid_updated_at",
                details="updated_at must be an ISO-8601 timestamp.",
            )
        )

    max_age_days, max_age_error = _resolve_max_age_days(payload)
    if max_age_error:
        violations.append(
            OwnerAttestationViolation(
                owner_team="*",
                reason="invalid_max_attestation_age_days",
                details=max_age_error,
            )
        )

    min_remaining_days, min_remaining_error = _resolve_min_remaining_days(payload)
    if min_remaining_error:
        violations.append(
            OwnerAttestationViolation(
                owner_team="*",
                reason="invalid_min_attestation_days_remaining",
                details=min_remaining_error,
            )
        )

    owners = payload.get("owners")
    if not isinstance(owners, list):
        violations.append(
            OwnerAttestationViolation(
                owner_team="*",
                reason="invalid_owners",
                details="owners must be a list.",
            )
        )
        return violations

    if not owners:
        violations.append(
            OwnerAttestationViolation(
                owner_team="*",
                reason="empty_owners",
                details="owners must not be empty.",
            )
        )

    owner_rows: dict[str, dict[str, Any]] = {}

    for index, owner in enumerate(owners):
        if not isinstance(owner, dict):
            violations.append(
                OwnerAttestationViolation(
                    owner_team=f"owners[{index}]",
                    reason="invalid_owner_entry",
                    details="owner entry must be an object.",
                )
            )
            continue

        owner_team = str(owner.get("owner_team", "")).strip()
        if not owner_team:
            violations.append(
                OwnerAttestationViolation(
                    owner_team=f"owners[{index}]",
                    reason="missing_owner_team",
                    details="owner_team must be a non-empty string.",
                )
            )
            continue

        if owner_team in owner_rows:
            violations.append(
                OwnerAttestationViolation(
                    owner_team=owner_team,
                    reason="duplicate_owner_team",
                    details="owner_team must be unique in owners.",
                )
            )
            continue

        owner_rows[owner_team] = owner

        attested_by = str(owner.get("attested_by", "")).strip()
        if not attested_by:
            violations.append(
                OwnerAttestationViolation(
                    owner_team=owner_team,
                    reason="missing_attested_by",
                    details="attested_by must be a non-empty string.",
                )
            )

        attested_at = _parse_iso8601(owner.get("attested_at"))
        if attested_at is None:
            violations.append(
                OwnerAttestationViolation(
                    owner_team=owner_team,
                    reason="invalid_attested_at",
                    details="attested_at must be an ISO-8601 timestamp.",
                )
            )
        else:
            age_days = (now - attested_at).total_seconds() / 86400
            if max_age_days is not None and age_days > max_age_days:
                violations.append(
                    OwnerAttestationViolation(
                        owner_team=owner_team,
                        reason="stale_attestation",
                        details=(
                            f"attestation age {age_days:.1f} days exceeds "
                            f"max {max_age_days} days."
                        ),
                    )
                )
            if (
                max_age_days is not None
                and min_remaining_days is not None
                and min_remaining_days > 0
                and age_days <= max_age_days
            ):
                remaining_days = max_age_days - age_days
                if remaining_days < min_remaining_days:
                    violations.append(
                        OwnerAttestationViolation(
                            owner_team=owner_team,
                            reason="attestation_expiring_soon",
                            details=(
                                f"attestation remaining {remaining_days:.1f} days is below "
                                f"minimum reminder threshold {min_remaining_days} days."
                            ),
                        )
                    )
            skew_seconds = (attested_at - now).total_seconds()
            if skew_seconds > MAX_FUTURE_SKEW_SECONDS:
                violations.append(
                    OwnerAttestationViolation(
                        owner_team=owner_team,
                        reason="future_attestation_timestamp",
                        details=(
                            "attested_at cannot be in the future beyond allowed skew "
                            f"({MAX_FUTURE_SKEW_SECONDS}s)."
                        ),
                    )
                )

        refs = owner.get("codeowners_refs")
        if not isinstance(refs, list) or not refs:
            violations.append(
                OwnerAttestationViolation(
                    owner_team=owner_team,
                    reason="invalid_codeowners_refs",
                    details="codeowners_refs must be a non-empty list.",
                )
            )
        else:
            for ref in refs:
                if not isinstance(ref, str) or not ref.startswith("/"):
                    violations.append(
                        OwnerAttestationViolation(
                            owner_team=owner_team,
                            reason="invalid_codeowners_ref",
                            details=f"invalid codeowners ref: {ref}",
                        )
                    )
                    continue
                if codeowner_refs and ref not in codeowner_refs:
                    violations.append(
                        OwnerAttestationViolation(
                            owner_team=owner_team,
                            reason="codeowners_ref_missing",
                            details=f"codeowners ref not found in .github/CODEOWNERS: {ref}",
                        )
                    )

    inventory_teams = _inventory_owner_teams(inventory)
    attested_teams = set(owner_rows)

    for missing_team in sorted(inventory_teams - attested_teams):
        violations.append(
            OwnerAttestationViolation(
                owner_team=missing_team,
                reason="missing_owner_attestation",
                details="owner_team exists in inventory but not in attestation file.",
            )
        )

    for stale_team in sorted(attested_teams - inventory_teams):
        violations.append(
            OwnerAttestationViolation(
                owner_team=stale_team,
                reason="stale_owner_attestation",
                details="owner_team attested but not present in current inventory.",
            )
        )

    if updated_at is not None:
        newest_attested_at = None
        for owner_team, owner in owner_rows.items():
            parsed = _parse_iso8601(owner.get("attested_at"))
            if parsed is None:
                continue
            if newest_attested_at is None or parsed > newest_attested_at:
                newest_attested_at = parsed
        if newest_attested_at is not None and updated_at < newest_attested_at:
            violations.append(
                OwnerAttestationViolation(
                    owner_team="*",
                    reason="updated_at_before_attested_at",
                    details="updated_at must be >= latest owners[].attested_at.",
                )
            )

    return violations


def run_policy_check() -> int:
    violations = collect_owner_attestation_violations()
    if not violations:
        print("[api-inventory-attestation] ok: owner attestation contract satisfied")
        return 0

    print("[api-inventory-attestation] failed:", file=sys.stderr)
    for item in violations:
        print(
            f"  - owner_team={item.owner_team} reason={item.reason} details={item.details}",
            file=sys.stderr,
        )
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
