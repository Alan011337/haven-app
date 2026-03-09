#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path

import certifi


REQUIRED_SLI_KEYS = {
    "notification_runtime",
    "dynamic_content_runtime",
}

REQUIRED_CHECK_KEYS = {
    "notification_outbox_depth",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate observability contract from a live /health/slo payload.")
    parser.add_argument("--health-slo-url", default="")
    parser.add_argument("--bearer-token", default="")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--allow-missing-url", action="store_true")
    parser.add_argument("--summary-path", default="")
    return parser.parse_args()


def _write_summary(path: str, payload: dict[str, object]) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def _iter_ssl_contexts() -> list[ssl.SSLContext]:
    return [
        ssl.create_default_context(),
        ssl.create_default_context(cafile=certifi.where()),
    ]


def _is_cert_verification_error(exc: BaseException) -> bool:
    if isinstance(exc, ssl.SSLCertVerificationError):
        return True
    if isinstance(exc, urllib.error.URLError):
        return isinstance(getattr(exc, "reason", None), ssl.SSLCertVerificationError)
    return False


def _fetch_payload(url: str, bearer_token: str, timeout_seconds: float) -> dict[str, object]:
    request = urllib.request.Request(url=url, method="GET")
    if bearer_token:
        request.add_header("Authorization", f"Bearer {bearer_token}")
    last_error: BaseException | None = None
    contexts = _iter_ssl_contexts()
    for index, ssl_context in enumerate(contexts):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds, context=ssl_context) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
            break
        except urllib.error.URLError as exc:
            last_error = exc
            should_retry_with_certifi = (
                index == 0
                and len(contexts) > 1
                and _is_cert_verification_error(exc)
            )
            if should_retry_with_certifi:
                continue
            raise
    else:
        if last_error is not None:
            raise last_error
        raise RuntimeError("failed to fetch health payload")

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("health payload must be an object")
    return data


def _derive_health_url(health_slo_url: str) -> str:
    stripped = health_slo_url.strip()
    if stripped.endswith("/health/slo"):
        return stripped[: -len("/slo")]
    return ""


def _merge_checks_from_health_endpoint(
    payload: dict[str, object],
    *,
    health_slo_url: str,
    bearer_token: str,
    timeout_seconds: float,
) -> dict[str, object]:
    if isinstance(payload.get("checks"), dict):
        return payload
    health_url = _derive_health_url(health_slo_url)
    if not health_url:
        return payload
    try:
        health_payload = _fetch_payload(health_url, bearer_token, timeout_seconds)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        return payload
    checks = health_payload.get("checks")
    if not isinstance(checks, dict):
        return payload
    merged_payload = dict(payload)
    merged_payload["checks"] = checks
    return merged_payload


def main() -> int:
    args = _parse_args()
    url = args.health_slo_url.strip()
    if not url:
        result = "skipped" if args.allow_missing_url else "fail"
        summary = {
            "result": result,
            "reasons": ["missing_health_slo_url"],
            "meta": {"missing_sli": sorted(REQUIRED_SLI_KEYS), "missing_checks": sorted(REQUIRED_CHECK_KEYS)},
        }
        _write_summary(args.summary_path, summary)
        print("[observability-live-contract] result")
        print(f"  result: {result}")
        print("  reasons: missing_health_slo_url")
        return 0 if result == "skipped" else 1

    try:
        payload = _fetch_payload(url, args.bearer_token.strip(), args.timeout_seconds)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        summary = {
            "result": "fail",
            "reasons": ["payload_fetch_failed"],
            "meta": {"error_type": type(exc).__name__},
        }
        _write_summary(args.summary_path, summary)
        print("[observability-live-contract] fail: payload_fetch_failed")
        print(f"  error_type: {type(exc).__name__}")
        return 1

    payload = _merge_checks_from_health_endpoint(
        payload,
        health_slo_url=url,
        bearer_token=args.bearer_token.strip(),
        timeout_seconds=args.timeout_seconds,
    )

    sli = payload.get("sli")
    checks = payload.get("checks")
    reasons: list[str] = []
    if not isinstance(sli, dict):
        reasons.append("sli_missing")
        sli = {}
    if not isinstance(checks, dict):
        reasons.append("checks_missing")
        checks = {}

    missing_sli = sorted(key for key in REQUIRED_SLI_KEYS if key not in sli)
    missing_checks = sorted(key for key in REQUIRED_CHECK_KEYS if key not in checks)
    if missing_sli:
        reasons.append("sli_keys_missing")
    if missing_checks:
        reasons.append("checks_keys_missing")

    result = "pass" if not reasons else "fail"
    summary = {
        "result": result,
        "reasons": reasons,
        "meta": {
            "missing_sli": missing_sli,
            "missing_checks": missing_checks,
            "health_slo_url": url,
        },
    }
    _write_summary(args.summary_path, summary)
    print("[observability-live-contract] result")
    print(f"  result: {result}")
    print(f"  missing_sli: {', '.join(missing_sli) if missing_sli else 'none'}")
    print(f"  missing_checks: {', '.join(missing_checks) if missing_checks else 'none'}")
    print(f"  reasons: {', '.join(reasons) if reasons else 'none'}")
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
