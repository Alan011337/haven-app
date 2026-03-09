#!/usr/bin/env python3
"""Run canary health guard and optionally trigger rollback hook on failure."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable
from urllib import error, request
from urllib.parse import urlparse

try:
    from check_slo_burn_rate_gate import evaluate_slo_payload
except ModuleNotFoundError:
    _SCRIPT_DIR = Path(__file__).resolve().parent
    _CHECKER_PATH = _SCRIPT_DIR / "check_slo_burn_rate_gate.py"
    _SPEC = importlib.util.spec_from_file_location("check_slo_burn_rate_gate", _CHECKER_PATH)
    if _SPEC is None or _SPEC.loader is None:
        raise RuntimeError(f"Unable to load checker module from {_CHECKER_PATH}")
    _MODULE = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(_MODULE)
    evaluate_slo_payload = _MODULE.evaluate_slo_payload

DEFAULT_DURATION_SECONDS = 300
DEFAULT_INTERVAL_SECONDS = 30
DEFAULT_MAX_FAILURES = 1
DEFAULT_HTTP_TIMEOUT_SECONDS = 10.0

HEALTH_URL_ENV_KEYS = ("CANARY_GUARD_HEALTH_SLO_URL", "SLO_GATE_HEALTH_SLO_URL")
HEALTH_TOKEN_ENV_KEYS = ("CANARY_GUARD_BEARER_TOKEN", "SLO_GATE_BEARER_TOKEN")
REQUIRE_SUFFICIENT_ENV_KEYS = (
    "CANARY_GUARD_REQUIRE_SUFFICIENT_DATA",
    "SLO_GATE_REQUIRE_SUFFICIENT_DATA",
)


def _parse_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None:
        return default
    normalized = str(raw).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _resolve_env(keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = os.getenv(key, "").strip()
        if value:
            return value
    return None


def _parse_positive_int(raw: str | None, *, default: int, name: str) -> int:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return value


def _parse_positive_float(raw: str | None, *, default: float, name: str) -> float:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return value


def _validate_http_url(name: str, url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"{name} must start with http:// or https://")
    if not parsed.netloc:
        raise ValueError(f"{name} must include host")
    return url


def _http_json_request(
    *,
    method: str,
    url: str,
    timeout_seconds: float,
    bearer_token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers: dict[str, str] = {"Accept": "application/json"}
    body: bytes | None = None
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, headers=headers, data=body, method=method.upper())
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            status_code = int(getattr(response, "status", response.getcode()))
            text_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        text_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {text_body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"request failed: {exc}") from exc

    if status_code >= 400:
        raise RuntimeError(f"HTTP {status_code}: {text_body}")

    if not text_body.strip():
        return {}
    try:
        parsed_body = json.loads(text_body)
    except json.JSONDecodeError:
        return {"raw": text_body}
    return parsed_body if isinstance(parsed_body, dict) else {"raw": parsed_body}


def _fetch_health_sample(
    *,
    health_url: str,
    health_bearer_token: str | None,
    timeout_seconds: float,
    require_sufficient_data: bool,
) -> tuple[bool, list[str], dict[str, str]]:
    payload = _http_json_request(
        method="GET",
        url=health_url,
        timeout_seconds=timeout_seconds,
        bearer_token=health_bearer_token,
    )
    if not isinstance(payload, dict):
        return False, ["invalid_health_payload"], {
            "ws": "missing",
            "ws_burn_rate": "missing",
            "cuj": "missing",
        }
    return evaluate_slo_payload(payload, require_sufficient_data=require_sufficient_data)


def _trigger_hook(
    *,
    hook_url: str,
    hook_bearer_token: str | None,
    timeout_seconds: float,
    action: str,
    details: dict[str, Any],
) -> None:
    payload = {
        "action": action,
        "source": "haven-canary-guard",
        "timestamp": int(time.time()),
        "details": details,
    }
    _http_json_request(
        method="POST",
        url=hook_url,
        timeout_seconds=timeout_seconds,
        bearer_token=hook_bearer_token,
        payload=payload,
    )


def run_canary_guard(
    *,
    health_url: str,
    health_bearer_token: str | None,
    require_sufficient_data: bool,
    duration_seconds: int,
    interval_seconds: int,
    max_failures: int,
    timeout_seconds: float,
    target_percent: float,
    rollout_hook_url: str | None,
    rollback_hook_url: str | None,
    hook_bearer_token: str | None,
    hook_timeout_seconds: float,
    dry_run_hooks: bool,
    fetch_sample_fn: Callable[..., tuple[bool, list[str], dict[str, str]]] = _fetch_health_sample,
    hook_fn: Callable[..., None] = _trigger_hook,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[bool, dict[str, Any]]:
    total_samples = max(1, duration_seconds // interval_seconds + 1)
    summary: dict[str, Any] = {
        "total_samples": total_samples,
        "failed_samples": 0,
        "pass_samples": 0,
        "fail_reasons": [],
    }

    if rollout_hook_url:
        rollout_details = {"target_percent": target_percent, "total_samples": total_samples}
        if dry_run_hooks:
            print("[canary-guard] dry-run rollout hook", rollout_details)
        else:
            hook_fn(
                hook_url=rollout_hook_url,
                hook_bearer_token=hook_bearer_token,
                timeout_seconds=hook_timeout_seconds,
                action="rollout",
                details=rollout_details,
            )
            print("[canary-guard] rollout hook triggered")

    last_statuses: dict[str, str] = {}
    for index in range(total_samples):
        passed, reasons, statuses = fetch_sample_fn(
            health_url=health_url,
            health_bearer_token=health_bearer_token,
            timeout_seconds=timeout_seconds,
            require_sufficient_data=require_sufficient_data,
        )
        last_statuses = statuses
        print(
            "[canary-guard] sample "
            f"{index + 1}/{total_samples}: "
            f"ws={statuses.get('ws', 'missing')} ws_burn_rate={statuses.get('ws_burn_rate', 'missing')} "
            f"cuj={statuses.get('cuj', 'missing')} "
            f"result={'pass' if passed else 'fail'}"
        )
        if passed:
            summary["pass_samples"] += 1
        else:
            summary["failed_samples"] += 1
            summary["fail_reasons"].append(reasons)
            if summary["failed_samples"] >= max_failures:
                break
        if index < total_samples - 1:
            sleep_fn(interval_seconds)

    summary["last_statuses"] = last_statuses
    if summary["failed_samples"] >= max_failures:
        failure_details = {
            "target_percent": target_percent,
            "failed_samples": summary["failed_samples"],
            "max_failures": max_failures,
            "last_statuses": summary["last_statuses"],
            "fail_reasons": summary["fail_reasons"],
        }
        if rollback_hook_url:
            if dry_run_hooks:
                print("[canary-guard] dry-run rollback hook", failure_details)
            else:
                hook_fn(
                    hook_url=rollback_hook_url,
                    hook_bearer_token=hook_bearer_token,
                    timeout_seconds=hook_timeout_seconds,
                    action="rollback",
                    details=failure_details,
                )
                print("[canary-guard] rollback hook triggered")
        return False, summary
    return True, summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run canary health guard against /health/slo and trigger rollback hook "
            "when WS SLI/burn-rate breaches policy."
        )
    )
    parser.add_argument("--health-url", default=None)
    parser.add_argument("--health-bearer-token", default=None)
    parser.add_argument("--duration-seconds", type=int, default=None)
    parser.add_argument("--interval-seconds", type=int, default=None)
    parser.add_argument("--max-failures", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--target-percent", type=float, default=None)
    parser.add_argument("--rollout-hook-url", default=None)
    parser.add_argument("--rollback-hook-url", default=None)
    parser.add_argument("--hook-bearer-token", default=None)
    parser.add_argument("--hook-timeout-seconds", type=float, default=None)
    parser.add_argument("--dry-run-hooks", action="store_true")
    parser.add_argument("--allow-missing-health-url", action="store_true")
    parser.add_argument("--require-sufficient-data", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    raw_health_url = (args.health_url or _resolve_env(HEALTH_URL_ENV_KEYS) or "").strip()
    if not raw_health_url:
        if args.allow_missing_health_url:
            print("[canary-guard] skipped: missing health URL")
            print("  set CANARY_GUARD_HEALTH_SLO_URL or SLO_GATE_HEALTH_SLO_URL")
            return 0
        print("[canary-guard] fail: missing health URL")
        return 1

    try:
        health_url = _validate_http_url("health-url", raw_health_url)
        rollout_hook_url = (
            _validate_http_url("rollout-hook-url", args.rollout_hook_url.strip())
            if args.rollout_hook_url
            else (
                _validate_http_url(
                    "rollout-hook-url",
                    os.getenv("CANARY_GUARD_ROLLOUT_HOOK_URL", "").strip(),
                )
                if os.getenv("CANARY_GUARD_ROLLOUT_HOOK_URL", "").strip()
                else None
            )
        )
        rollback_hook_url = (
            _validate_http_url("rollback-hook-url", args.rollback_hook_url.strip())
            if args.rollback_hook_url
            else (
                _validate_http_url(
                    "rollback-hook-url",
                    os.getenv("CANARY_GUARD_ROLLBACK_HOOK_URL", "").strip(),
                )
                if os.getenv("CANARY_GUARD_ROLLBACK_HOOK_URL", "").strip()
                else None
            )
        )
    except ValueError as exc:
        print("[canary-guard] fail: invalid URL config")
        print(f"  detail: {exc}")
        return 1

    health_bearer_token = (
        args.health_bearer_token
        if args.health_bearer_token is not None
        else (_resolve_env(HEALTH_TOKEN_ENV_KEYS) or None)
    )
    hook_bearer_token = (
        args.hook_bearer_token
        if args.hook_bearer_token is not None
        else (os.getenv("CANARY_GUARD_HOOK_BEARER_TOKEN", "").strip() or None)
    )

    try:
        duration_seconds = _parse_positive_int(
            str(args.duration_seconds) if args.duration_seconds is not None else os.getenv("CANARY_GUARD_DURATION_SECONDS"),
            default=DEFAULT_DURATION_SECONDS,
            name="duration-seconds",
        )
        interval_seconds = _parse_positive_int(
            str(args.interval_seconds) if args.interval_seconds is not None else os.getenv("CANARY_GUARD_INTERVAL_SECONDS"),
            default=DEFAULT_INTERVAL_SECONDS,
            name="interval-seconds",
        )
        max_failures = _parse_positive_int(
            str(args.max_failures) if args.max_failures is not None else os.getenv("CANARY_GUARD_MAX_FAILURES"),
            default=DEFAULT_MAX_FAILURES,
            name="max-failures",
        )
        timeout_seconds = _parse_positive_float(
            str(args.timeout_seconds) if args.timeout_seconds is not None else os.getenv("CANARY_GUARD_TIMEOUT_SECONDS"),
            default=DEFAULT_HTTP_TIMEOUT_SECONDS,
            name="timeout-seconds",
        )
        hook_timeout_seconds = _parse_positive_float(
            str(args.hook_timeout_seconds)
            if args.hook_timeout_seconds is not None
            else os.getenv("CANARY_GUARD_HOOK_TIMEOUT_SECONDS"),
            default=DEFAULT_HTTP_TIMEOUT_SECONDS,
            name="hook-timeout-seconds",
        )
        target_percent = _parse_positive_float(
            str(args.target_percent) if args.target_percent is not None else os.getenv("CANARY_GUARD_TARGET_PERCENT"),
            default=1.0,
            name="target-percent",
        )
    except ValueError as exc:
        print("[canary-guard] fail: invalid numeric config")
        print(f"  detail: {exc}")
        return 1

    if target_percent > 100:
        print("[canary-guard] fail: target-percent must be <= 100")
        return 1

    if interval_seconds > duration_seconds:
        print("[canary-guard] fail: interval-seconds must be <= duration-seconds")
        return 1

    require_sufficient_data = args.require_sufficient_data or _parse_bool(
        _resolve_env(REQUIRE_SUFFICIENT_ENV_KEYS),
        default=False,
    )

    print("[canary-guard] configuration")
    print(f"  health_url: {health_url}")
    print(f"  duration_seconds: {duration_seconds}")
    print(f"  interval_seconds: {interval_seconds}")
    print(f"  max_failures: {max_failures}")
    print(f"  require_sufficient_data: {'yes' if require_sufficient_data else 'no'}")
    print(f"  target_percent: {target_percent}")
    print(f"  rollout_hook_configured: {'yes' if rollout_hook_url else 'no'}")
    print(f"  rollback_hook_configured: {'yes' if rollback_hook_url else 'no'}")
    print(f"  dry_run_hooks: {'yes' if args.dry_run_hooks else 'no'}")

    try:
        passed, summary = run_canary_guard(
            health_url=health_url,
            health_bearer_token=health_bearer_token,
            require_sufficient_data=require_sufficient_data,
            duration_seconds=duration_seconds,
            interval_seconds=interval_seconds,
            max_failures=max_failures,
            timeout_seconds=timeout_seconds,
            target_percent=target_percent,
            rollout_hook_url=rollout_hook_url,
            rollback_hook_url=rollback_hook_url,
            hook_bearer_token=hook_bearer_token,
            hook_timeout_seconds=hook_timeout_seconds,
            dry_run_hooks=args.dry_run_hooks,
        )
    except RuntimeError as exc:
        print("[canary-guard] fail: runtime error")
        print(f"  detail: {exc}")
        return 1

    print("[canary-guard] summary")
    print(f"  total_samples: {summary.get('total_samples')}")
    print(f"  pass_samples: {summary.get('pass_samples')}")
    print(f"  failed_samples: {summary.get('failed_samples')}")

    if not passed:
        print("[canary-guard] result: fail")
        return 1

    print("[canary-guard] result: pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
