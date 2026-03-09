#!/usr/bin/env python3
"""Evaluate timeline runtime clamp pressure from /health/slo payload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


def _load_payload(*, health_slo_url: str | None, health_slo_file: str | None, timeout_seconds: float) -> dict[str, Any]:
    if health_slo_file:
        return json.loads(Path(health_slo_file).read_text(encoding="utf-8"))
    if not health_slo_url:
        raise RuntimeError("health slo payload source missing; pass --health-slo-url or --health-slo-file")
    request = Request(health_slo_url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=max(1.0, float(timeout_seconds))) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(f"health slo fetch failed: {exc.reason}") from exc


def _to_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        return int(float(value))
    return 0


def evaluate_timeline_runtime(
    *,
    payload: dict[str, Any],
    min_query_total: int,
    clamp_ratio_warn: float,
    clamp_ratio_critical: float,
) -> tuple[str, list[str], dict[str, Any]]:
    sli = payload.get("sli") if isinstance(payload.get("sli"), dict) else {}
    timeline_runtime = sli.get("timeline_runtime") if isinstance(sli.get("timeline_runtime"), dict) else {}
    counters = timeline_runtime.get("counters") if isinstance(timeline_runtime.get("counters"), dict) else {}

    query_total = max(0, _to_int(counters.get("timeline_query_total")))
    clamped_total = max(0, _to_int(counters.get("timeline_budget_clamped_total")))
    clamp_ratio = (float(clamped_total) / float(query_total)) if query_total > 0 else 0.0

    reasons: list[str] = []
    if query_total < max(0, int(min_query_total)):
        result = "insufficient_data"
        reasons.append("insufficient_query_volume")
    elif clamp_ratio > clamp_ratio_critical:
        result = "critical"
        reasons.append("timeline_budget_clamp_ratio_above_critical_threshold")
    elif clamp_ratio > clamp_ratio_warn:
        result = "degraded"
        reasons.append("timeline_budget_clamp_ratio_above_warn_threshold")
    else:
        result = "pass"

    meta = {
        "query_total": query_total,
        "clamped_total": clamped_total,
        "clamp_ratio": round(clamp_ratio, 6),
        "min_query_total": int(min_query_total),
        "clamp_ratio_warn_threshold": float(clamp_ratio_warn),
        "clamp_ratio_critical_threshold": float(clamp_ratio_critical),
    }
    return result, reasons, meta


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Timeline runtime clamp pressure gate.")
    parser.add_argument("--health-slo-url", default=None)
    parser.add_argument("--health-slo-file", default=None)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--min-query-total", type=int, default=20)
    parser.add_argument("--max-clamp-ratio-warn", type=float, default=0.15)
    parser.add_argument("--max-clamp-ratio-critical", type=float, default=0.30)
    parser.add_argument("--allow-missing-payload", action="store_true")
    parser.add_argument("--fail-on-alert", action="store_true")
    parser.add_argument("--summary-path", default=None)
    return parser.parse_args()


def _write_summary(*, summary_path: str | None, payload: dict[str, Any]) -> None:
    if not summary_path:
        return
    path = Path(summary_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    try:
        payload = _load_payload(
            health_slo_url=args.health_slo_url,
            health_slo_file=args.health_slo_file,
            timeout_seconds=args.timeout_seconds,
        )
    except Exception as exc:
        if args.allow_missing_payload:
            summary = {
                "result": "skipped",
                "reasons": ["missing_payload"],
                "meta": {"error": str(exc)},
            }
            _write_summary(summary_path=args.summary_path, payload=summary)
            print("[timeline-runtime-gate] skipped: missing payload")
            return 0
        print(f"[timeline-runtime-gate] fail: {exc}")
        return 1

    result, reasons, meta = evaluate_timeline_runtime(
        payload=payload,
        min_query_total=args.min_query_total,
        clamp_ratio_warn=args.max_clamp_ratio_warn,
        clamp_ratio_critical=args.max_clamp_ratio_critical,
    )

    summary = {"result": result, "reasons": reasons, "meta": meta}
    _write_summary(summary_path=args.summary_path, payload=summary)

    print("[timeline-runtime-gate] result")
    print(f"  status: {result}")
    print(f"  reasons: {reasons or []}")
    print(f"  query_total: {meta['query_total']}")
    print(f"  clamped_total: {meta['clamped_total']}")
    print(f"  clamp_ratio: {meta['clamp_ratio']}")
    print(f"  warn_threshold: {meta['clamp_ratio_warn_threshold']}")
    print(f"  critical_threshold: {meta['clamp_ratio_critical_threshold']}")

    if args.fail_on_alert and result in {"degraded", "critical"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
