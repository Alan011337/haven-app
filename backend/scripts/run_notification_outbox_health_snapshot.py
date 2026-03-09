#!/usr/bin/env python3
"""Capture a compact outbox-focused health snapshot for on-call triage."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


def _load_payload(*, health_url: str | None, health_file: str | None, timeout_seconds: float) -> dict[str, Any]:
    if health_file:
        return json.loads(Path(health_file).read_text(encoding="utf-8"))
    if not health_url:
        raise RuntimeError("health payload source missing; pass --health-url or --health-file")
    request = Request(health_url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=max(1.0, float(timeout_seconds))) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(f"health fetch failed: {exc.reason}") from exc


def _build_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    outbox_status = checks.get("notification_outbox_status") or {}
    degraded_reasons = payload.get("degraded_reasons") if isinstance(payload.get("degraded_reasons"), list) else []
    outbox_related_reasons = [reason for reason in degraded_reasons if "outbox" in str(reason).lower()]

    return {
        "captured_at": datetime.now(UTC).isoformat(),
        "health_status": payload.get("status"),
        "outbox": {
            "status": outbox_status if isinstance(outbox_status, dict) else {},
            "depth": checks.get("notification_outbox_depth"),
            "oldest_pending_age_seconds": checks.get("notification_outbox_oldest_pending_age_seconds"),
            "retry_age_p95_seconds": checks.get("notification_outbox_retry_age_p95_seconds"),
            "dead_letter_rate": checks.get("notification_outbox_dead_letter_rate"),
            "stale_processing_count": checks.get("notification_outbox_stale_processing_count"),
            "dispatch_lock_heartbeat_age_seconds": checks.get(
                "notification_outbox_dispatch_lock_heartbeat_age_seconds"
            ),
        },
        "degraded_reasons": outbox_related_reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture notification outbox health snapshot.")
    parser.add_argument("--health-url", default=None, help="Health endpoint URL (defaults to none).")
    parser.add_argument("--health-file", default=None, help="Use local JSON payload instead of HTTP.")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=10.0,
        help="HTTP timeout when fetching health URL.",
    )
    parser.add_argument(
        "--output",
        default="/tmp/notification-outbox-health-snapshot.json",
        help="Output path for snapshot JSON.",
    )
    args = parser.parse_args()

    payload = _load_payload(
        health_url=args.health_url,
        health_file=args.health_file,
        timeout_seconds=args.timeout_seconds,
    )
    snapshot = _build_snapshot(payload)
    output_path = Path(args.output)
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("[outbox-health-snapshot] result")
    print(f"  output: {output_path}")
    print(f"  health_status: {snapshot.get('health_status')}")
    print(f"  outbox_depth: {snapshot.get('outbox', {}).get('depth')}")
    print(f"  degraded_reasons: {snapshot.get('degraded_reasons') or []}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

