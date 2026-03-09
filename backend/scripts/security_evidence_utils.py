from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_RIGHTS_FIRE_DRILL_KIND = "data-rights-fire-drill"
BILLING_FIRE_DRILL_KIND = "billing-fire-drill"

_EVIDENCE_GLOB_BY_KIND: dict[str, str] = {
    "p0-drill": "p0-drill-*.json",
    DATA_RIGHTS_FIRE_DRILL_KIND: "data-rights-fire-drill-*.json",
    BILLING_FIRE_DRILL_KIND: "billing-fire-drill-*.json",
    "billing-reconciliation": "billing-reconciliation-*.json",
    "billing-console-drift": "billing-console-drift-*.json",
    "audit-log-retention": "audit-log-retention-*.json",
    "data-soft-delete-purge": "data-soft-delete-purge-*.json",
    "key-rotation-drill": "key-rotation-drill-*.json",
    "data-restore-drill": "data-restore-drill-*.json",
    "backup-restore-drill": "backup-restore-drill-*.json",
    "chaos-drill": "chaos-drill-*.json",
}


def parse_iso8601(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def parse_iso8601_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and value >= 0


def resolve_latest_evidence_path(*, evidence_dir: Path, kind: str) -> Path:
    pattern = _EVIDENCE_GLOB_BY_KIND.get(kind)
    if not pattern:
        raise ValueError(f"Unsupported evidence kind: {kind}")
    candidates = sorted(evidence_dir.glob(pattern))
    if not candidates and kind in {DATA_RIGHTS_FIRE_DRILL_KIND, BILLING_FIRE_DRILL_KIND}:
        # Backward compatibility while transitioning to dedicated subset artifacts.
        candidates = sorted(evidence_dir.glob("p0-drill-*.json"))
    if not candidates:
        raise FileNotFoundError(f"No evidence files found for kind={kind} under {evidence_dir}")
    return candidates[-1]
