#!/usr/bin/env python3
"""Build an on-call runtime snapshot from /health and /health/slo payloads."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


def _load_json_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("snapshot root must be object")
    return payload


def _fetch_json(url: str, timeout_seconds: float) -> dict[str, Any]:
    req = request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with request.urlopen(req, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("health response root must be object")
    return payload


def _extract_summary(*, health: dict[str, Any], slo: dict[str, Any]) -> dict[str, Any]:
    checks = health.get("checks") if isinstance(health.get("checks"), dict) else {}
    sli = slo.get("sli") if isinstance(slo.get("sli"), dict) else {}
    evaluation = sli.get("evaluation") if isinstance(sli.get("evaluation"), dict) else {}
    ai_router_runtime = sli.get("ai_router_runtime") if isinstance(sli.get("ai_router_runtime"), dict) else {}
    dynamic_runtime = sli.get("dynamic_content_runtime") if isinstance(sli.get("dynamic_content_runtime"), dict) else {}
    events_runtime = sli.get("events_runtime") if isinstance(sli.get("events_runtime"), dict) else {}

    return {
        "health_status": health.get("status", "unknown"),
        "health_degraded_reasons": health.get("degraded_reasons", []),
        "database_status": (checks.get("database") or {}).get("status"),
        "redis_status": (checks.get("redis") or {}).get("status"),
        "notification_outbox_depth": checks.get("notification_outbox_depth"),
        "notification_outbox_retry_age_p95_seconds": checks.get(
            "notification_outbox_retry_age_p95_seconds"
        ),
        "dynamic_content_fallback_ratio": checks.get("dynamic_content_fallback_ratio"),
        "slo_ws_status": (evaluation.get("ws") or {}).get("status"),
        "slo_ws_burn_rate_status": (evaluation.get("ws_burn_rate") or {}).get("status"),
        "slo_ai_router_burn_rate_status": (evaluation.get("ai_router_burn_rate") or {}).get("status"),
        "slo_push_status": (evaluation.get("push") or {}).get("status"),
        "slo_cuj_status": (evaluation.get("cuj") or {}).get("status"),
        "slo_abuse_economics_status": ((sli.get("abuse_economics") or {}).get("evaluation") or {}).get("status"),
        "ai_router_runtime_state": ai_router_runtime.get("state", {}),
        "dynamic_content_runtime_state": dynamic_runtime.get("state", {}),
        "events_ingest_guard_state": events_runtime.get("ingest_guard", {}),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture on-call runtime snapshot.")
    parser.add_argument("--health-url", default="http://127.0.0.1:8000/health")
    parser.add_argument("--health-slo-url", default="http://127.0.0.1:8000/health/slo")
    parser.add_argument("--health-file", default=None, help="Optional local /health payload file.")
    parser.add_argument("--health-slo-file", default=None, help="Optional local /health/slo payload file.")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--output", default="/tmp/oncall-runtime-snapshot.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.health_file:
            health_payload = _load_json_file(Path(args.health_file))
        else:
            health_payload = _fetch_json(args.health_url, args.timeout_seconds)

        if args.health_slo_file:
            slo_payload = _load_json_file(Path(args.health_slo_file))
        else:
            slo_payload = _fetch_json(args.health_slo_url, args.timeout_seconds)
    except (OSError, ValueError, json.JSONDecodeError, error.URLError, error.HTTPError) as exc:
        print(f"[oncall-runtime-snapshot] fail: {type(exc).__name__}")
        return 1

    summary = _extract_summary(health=health_payload, slo=slo_payload)
    payload = {
        "artifact_kind": "oncall-runtime-snapshot",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "backend/scripts/run_oncall_runtime_snapshot.py",
        "summary": summary,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[oncall-runtime-snapshot] wrote: {output_path}")
    print(f"[oncall-runtime-snapshot] health_status={summary['health_status']} slo_ws_status={summary['slo_ws_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
