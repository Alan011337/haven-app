#!/usr/bin/env python3
"""Burn-rate based deploy gate checker for /health/slo payload."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
from typing import Any
from urllib import error, request
from urllib.parse import urlparse

import certifi

DEFAULT_TIMEOUT_SECONDS = 10.0
URL_ENV_KEY = "SLO_GATE_HEALTH_SLO_URL"
FILE_ENV_KEY = "SLO_GATE_HEALTH_SLO_FILE"
TOKEN_ENV_KEY = "SLO_GATE_BEARER_TOKEN"
TIMEOUT_ENV_KEY = "SLO_GATE_TIMEOUT_SECONDS"
REQUIRE_SUFFICIENT_ENV_KEY = "SLO_GATE_REQUIRE_SUFFICIENT_DATA"
FAIL_ON_ABUSE_WARN_ENV_KEY = "SLO_GATE_FAIL_ON_ABUSE_WARN"


def _parse_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None:
        return default
    normalized = str(raw).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _resolve_timeout(raw: str | None) -> float:
    if raw is None or str(raw).strip() == "":
        return DEFAULT_TIMEOUT_SECONDS
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise ValueError("timeout must be a number") from exc
    if timeout <= 0:
        raise ValueError("timeout must be greater than 0")
    return timeout


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("url must start with http:// or https://")
    if not parsed.netloc:
        raise ValueError("url must include host")
    return url


def _iter_ssl_contexts() -> list[ssl.SSLContext]:
    return [
        ssl.create_default_context(),
        ssl.create_default_context(cafile=certifi.where()),
    ]


def _is_cert_verification_error(exc: BaseException) -> bool:
    if isinstance(exc, ssl.SSLCertVerificationError):
        return True
    if isinstance(exc, error.URLError):
        return isinstance(getattr(exc, "reason", None), ssl.SSLCertVerificationError)
    return False


def _fetch_json_payload(*, url: str, timeout_seconds: float, bearer_token: str | None) -> dict[str, Any]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    req = request.Request(url, headers=headers, method="GET")
    last_url_error: error.URLError | None = None
    for index, ssl_context in enumerate(_iter_ssl_contexts()):
        try:
            with request.urlopen(req, timeout=timeout_seconds, context=ssl_context) as response:
                status_code = int(getattr(response, "status", response.getcode()))
                body = response.read().decode("utf-8")
            break
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"health endpoint returned HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            last_url_error = exc
            should_retry_with_certifi = (
                index == 0
                and _is_cert_verification_error(exc)
            )
            if should_retry_with_certifi:
                continue
            raise RuntimeError(f"failed to reach health endpoint: {exc}") from exc
    else:
        if last_url_error is not None:
            raise RuntimeError(f"failed to reach health endpoint: {last_url_error}") from last_url_error
        raise RuntimeError("failed to reach health endpoint")

    if status_code >= 400:
        raise RuntimeError(f"health endpoint returned HTTP {status_code}: {body}")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("health endpoint response is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("health endpoint JSON root must be an object")
    return payload


def _load_json_payload_from_file(file_path: str) -> dict[str, Any]:
    try:
        with open(file_path, encoding="utf-8") as fp:
            payload = json.load(fp)
    except OSError as exc:
        raise RuntimeError(f"failed to read payload file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("payload file is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("payload file JSON root must be an object")
    return payload


def _safe_status(value: Any) -> str:
    if not isinstance(value, str):
        return "missing"
    normalized = value.strip().lower()
    return normalized or "missing"


def evaluate_slo_payload(
    payload: dict[str, Any],
    *,
    require_sufficient_data: bool = False,
    fail_on_abuse_warn: bool = False,
) -> tuple[bool, list[str], dict[str, str]]:
    reasons: list[str] = []
    sli = payload.get("sli")
    if not isinstance(sli, dict):
        return False, ["missing_sli_payload"], {
            "ws": "missing",
            "ws_burn_rate": "missing",
            "ai_router_burn_rate": "missing",
            "push": "missing",
            "cuj": "missing",
            "abuse_economics": "missing",
        }

    evaluation = sli.get("evaluation")
    if not isinstance(evaluation, dict):
        return False, ["missing_sli_evaluation"], {
            "ws": "missing",
            "ws_burn_rate": "missing",
            "ai_router_burn_rate": "missing",
            "push": "missing",
            "cuj": "missing",
            "abuse_economics": "missing",
        }

    ws_eval = evaluation.get("ws")
    ws_burn_eval = evaluation.get("ws_burn_rate")
    ai_router_burn_eval = evaluation.get("ai_router_burn_rate")
    push_eval = evaluation.get("push")
    cuj_eval = evaluation.get("cuj")
    ws_status = _safe_status(ws_eval.get("status") if isinstance(ws_eval, dict) else None)
    ws_burn_status = _safe_status(
        ws_burn_eval.get("status") if isinstance(ws_burn_eval, dict) else None
    )
    ai_router_burn_status = _safe_status(
        ai_router_burn_eval.get("status")
        if isinstance(ai_router_burn_eval, dict)
        else None
    )
    if ai_router_burn_status == "missing":
        ai_router_burn_status = "insufficient_data"
    push_status = _safe_status(push_eval.get("status") if isinstance(push_eval, dict) else None)
    if push_status == "missing":
        push_status = "insufficient_data"
    # Backward-compatible rollout: missing CUJ snapshot is treated as insufficient_data.
    cuj_status = _safe_status(cuj_eval.get("status") if isinstance(cuj_eval, dict) else None)
    if cuj_status == "missing":
        cuj_status = "insufficient_data"
    abuse_sli = sli.get("abuse_economics")
    abuse_evaluation = (
        abuse_sli.get("evaluation")
        if isinstance(abuse_sli, dict)
        else {}
    )
    abuse_status = _safe_status(
        abuse_evaluation.get("status") if isinstance(abuse_evaluation, dict) else None
    )
    if abuse_status == "missing":
        abuse_status = "insufficient_data"

    statuses = {
        "ws": ws_status,
        "ws_burn_rate": ws_burn_status,
        "ai_router_burn_rate": ai_router_burn_status,
        "push": push_status,
        "cuj": cuj_status,
        "abuse_economics": abuse_status,
    }

    allowed_statuses = {"ok", "insufficient_data", "degraded"}
    if ws_status not in allowed_statuses:
        reasons.append(f"unexpected_ws_status:{ws_status}")
    if ws_burn_status not in allowed_statuses:
        reasons.append(f"unexpected_ws_burn_rate_status:{ws_burn_status}")
    if ai_router_burn_status not in allowed_statuses:
        reasons.append(f"unexpected_ai_router_burn_rate_status:{ai_router_burn_status}")
    if push_status not in allowed_statuses:
        reasons.append(f"unexpected_push_status:{push_status}")
    if cuj_status not in allowed_statuses:
        reasons.append(f"unexpected_cuj_status:{cuj_status}")
    if abuse_status not in {"ok", "warn", "block", "insufficient_data"}:
        reasons.append(f"unexpected_abuse_economics_status:{abuse_status}")

    if ws_status == "degraded":
        reasons.append("ws_sli_degraded")
    if ws_burn_status == "degraded":
        reasons.append("ws_burn_rate_degraded")
    if ai_router_burn_status == "degraded":
        reasons.append("ai_router_burn_rate_degraded")
    if push_status == "degraded":
        reasons.append("push_sli_degraded")
    if cuj_status == "degraded":
        reasons.append("cuj_sli_degraded")
    if abuse_status == "block":
        reasons.append("abuse_economics_block")
    if abuse_status == "warn" and fail_on_abuse_warn:
        reasons.append("abuse_economics_warn")

    if require_sufficient_data:
        if ws_status == "insufficient_data":
            reasons.append("ws_sli_insufficient_data")
        if ws_burn_status == "insufficient_data":
            reasons.append("ws_burn_rate_insufficient_data")
        if ai_router_burn_status == "insufficient_data":
            reasons.append("ai_router_burn_rate_insufficient_data")
        if push_status == "insufficient_data":
            reasons.append("push_sli_insufficient_data")
        if cuj_status == "insufficient_data":
            reasons.append("cuj_sli_insufficient_data")
        if abuse_status == "insufficient_data":
            reasons.append("abuse_economics_insufficient_data")

    return len(reasons) == 0, reasons, statuses


def _write_summary_file(
    summary_path: str | None,
    *,
    result: str,
    reasons: list[str],
    statuses: dict[str, str],
    require_sufficient_data: bool,
    fail_on_abuse_warn: bool,
    allow_missing_url: bool,
    url_configured: bool,
    source_type: str,
    payload_file_configured: bool,
) -> None:
    if not summary_path:
        return
    payload = {
        "result": result,
        "reasons": reasons,
        "statuses": statuses,
        "require_sufficient_data": require_sufficient_data,
        "fail_on_abuse_warn": fail_on_abuse_warn,
        "allow_missing_url": allow_missing_url,
        "url_configured": url_configured,
        "source_type": source_type,
        "payload_file_configured": payload_file_configured,
    }
    try:
        with open(summary_path, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, sort_keys=True, ensure_ascii=True)
            fp.write("\n")
    except OSError as exc:
        print("[slo-burn-rate-gate] warn: failed to write summary file")
        print(f"  path: {summary_path}")
        print(f"  detail: {exc}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate /health/slo evaluation status and fail deployment gate when "
            "WS/CUJ SLI or WS burn-rate is degraded."
        )
    )
    parser.add_argument(
        "--url",
        default=None,
        help=f"Health snapshot URL. Defaults to ${URL_ENV_KEY}.",
    )
    parser.add_argument(
        "--payload-file",
        default=None,
        help=(
            "Local health snapshot JSON file path for local/dev fallback. "
            f"Defaults to ${FILE_ENV_KEY}."
        ),
    )
    parser.add_argument(
        "--bearer-token",
        default=None,
        help=f"Bearer token for health endpoint auth. Defaults to ${TOKEN_ENV_KEY}.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help=f"HTTP timeout seconds. Defaults to ${TIMEOUT_ENV_KEY} or {DEFAULT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--allow-missing-url",
        action="store_true",
        help="Exit successfully when URL is missing (useful for PR/local dry-run).",
    )
    parser.add_argument(
        "--require-sufficient-data",
        action="store_true",
        help=(
            "Fail gate if WS or WS burn-rate status is `insufficient_data`. "
            f"Can also be controlled via ${REQUIRE_SUFFICIENT_ENV_KEY}=true."
        ),
    )
    parser.add_argument(
        "--summary-path",
        default=None,
        help=(
            "Optional path to write gate summary JSON. "
            "Intended for CI step summaries and triage automation."
        ),
    )
    parser.add_argument(
        "--fail-on-abuse-warn",
        action="store_true",
        help=(
            "Fail gate when abuse economics status is `warn`. "
            f"Can also be controlled via ${FAIL_ON_ABUSE_WARN_ENV_KEY}=true."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    summary_path = (args.summary_path or "").strip() or None
    allow_missing_url = bool(args.allow_missing_url)
    payload_file = (args.payload_file or os.getenv(FILE_ENV_KEY, "")).strip()
    require_sufficient_data = args.require_sufficient_data or _parse_bool(
        os.getenv(REQUIRE_SUFFICIENT_ENV_KEY),
        default=False,
    )
    fail_on_abuse_warn = args.fail_on_abuse_warn or _parse_bool(
        os.getenv(FAIL_ON_ABUSE_WARN_ENV_KEY),
        default=False,
    )
    default_statuses = {
        "ws": "missing",
        "ws_burn_rate": "missing",
        "ai_router_burn_rate": "missing",
        "push": "missing",
        "cuj": "missing",
        "abuse_economics": "missing",
    }

    def _exit_with_summary(
        *,
        result: str,
        reasons: list[str],
        statuses: dict[str, str] | None = None,
        url_configured: bool,
        source_type: str,
    ) -> int:
        _write_summary_file(
            summary_path,
            result=result,
            reasons=reasons,
            statuses=statuses or default_statuses,
            require_sufficient_data=require_sufficient_data,
            fail_on_abuse_warn=fail_on_abuse_warn,
            allow_missing_url=allow_missing_url,
            url_configured=url_configured,
            source_type=source_type,
            payload_file_configured=bool(payload_file),
        )
        return 0 if result in {"pass", "skip"} else 1

    raw_url = (args.url or os.getenv(URL_ENV_KEY, "")).strip()
    if not raw_url:
        if payload_file:
            print("[slo-burn-rate-gate] checking local health snapshot file")
            print(f"  payload_file: {payload_file}")
            print(f"  require_sufficient_data: {'yes' if require_sufficient_data else 'no'}")
            print(f"  fail_on_abuse_warn: {'yes' if fail_on_abuse_warn else 'no'}")
            try:
                payload = _load_json_payload_from_file(payload_file)
            except RuntimeError as exc:
                print("[slo-burn-rate-gate] fail: payload file error")
                print(f"  detail: {exc}")
                return _exit_with_summary(
                    result="fail",
                    reasons=["payload_file_error"],
                    url_configured=False,
                    source_type="file",
                )

            passed, reasons, statuses = evaluate_slo_payload(
                payload,
                require_sufficient_data=require_sufficient_data,
                fail_on_abuse_warn=fail_on_abuse_warn,
            )
            print(f"  ws_status: {statuses.get('ws', 'missing')}")
            print(f"  ws_burn_rate_status: {statuses.get('ws_burn_rate', 'missing')}")
            print(
                f"  ai_router_burn_rate_status: {statuses.get('ai_router_burn_rate', 'missing')}"
            )
            print(f"  push_status: {statuses.get('push', 'missing')}")
            print(f"  cuj_status: {statuses.get('cuj', 'missing')}")
            print(f"  abuse_economics_status: {statuses.get('abuse_economics', 'missing')}")
            if not passed:
                print("[slo-burn-rate-gate] result: fail")
                print("  reasons:")
                for reason in reasons:
                    print(f"    - {reason}")
                return _exit_with_summary(
                    result="fail",
                    reasons=reasons,
                    statuses=statuses,
                    url_configured=False,
                    source_type="file",
                )

            print("[slo-burn-rate-gate] result: pass")
            return _exit_with_summary(
                result="pass",
                reasons=[],
                statuses=statuses,
                url_configured=False,
                source_type="file",
            )

        if allow_missing_url:
            print("[slo-burn-rate-gate] skipped: missing URL")
            print(f"  set {URL_ENV_KEY} or pass --url to enforce this gate")
            return _exit_with_summary(
                result="skip",
                reasons=["missing_url"],
                url_configured=False,
                source_type="none",
            )
        print("[slo-burn-rate-gate] fail: missing URL")
        print(f"  required: {URL_ENV_KEY}, --url, {FILE_ENV_KEY}, or --payload-file")
        return _exit_with_summary(
            result="fail",
            reasons=["missing_url"],
            url_configured=False,
            source_type="none",
        )

    try:
        url = _validate_url(raw_url)
    except ValueError as exc:
        print("[slo-burn-rate-gate] fail: invalid URL")
        print(f"  detail: {exc}")
        return _exit_with_summary(
            result="fail",
            reasons=["invalid_url"],
            url_configured=True,
            source_type="url",
        )

    bearer_token = (args.bearer_token or os.getenv(TOKEN_ENV_KEY, "")).strip() or None
    try:
        timeout_seconds = (
            float(args.timeout_seconds)
            if args.timeout_seconds is not None
            else _resolve_timeout(os.getenv(TIMEOUT_ENV_KEY))
        )
    except ValueError as exc:
        print("[slo-burn-rate-gate] fail: invalid timeout")
        print(f"  detail: {exc}")
        return _exit_with_summary(
            result="fail",
            reasons=["invalid_timeout"],
            url_configured=True,
            source_type="url",
        )

    print("[slo-burn-rate-gate] checking /health/slo")
    print(f"  url: {url}")
    print(f"  timeout_seconds: {timeout_seconds}")
    print(f"  require_sufficient_data: {'yes' if require_sufficient_data else 'no'}")
    print(f"  fail_on_abuse_warn: {'yes' if fail_on_abuse_warn else 'no'}")

    try:
        payload = _fetch_json_payload(
            url=url,
            timeout_seconds=timeout_seconds,
            bearer_token=bearer_token,
        )
    except RuntimeError as exc:
        print("[slo-burn-rate-gate] fail: request error")
        print(f"  detail: {exc}")
        return _exit_with_summary(
            result="fail",
            reasons=["request_error"],
            url_configured=True,
            source_type="url",
        )

    passed, reasons, statuses = evaluate_slo_payload(
        payload,
        require_sufficient_data=require_sufficient_data,
        fail_on_abuse_warn=fail_on_abuse_warn,
    )
    print(f"  ws_status: {statuses.get('ws', 'missing')}")
    print(f"  ws_burn_rate_status: {statuses.get('ws_burn_rate', 'missing')}")
    print(f"  ai_router_burn_rate_status: {statuses.get('ai_router_burn_rate', 'missing')}")
    print(f"  push_status: {statuses.get('push', 'missing')}")
    print(f"  cuj_status: {statuses.get('cuj', 'missing')}")
    print(f"  abuse_economics_status: {statuses.get('abuse_economics', 'missing')}")

    if not passed:
        print("[slo-burn-rate-gate] result: fail")
        print("  reasons:")
        for reason in reasons:
            print(f"    - {reason}")
        return _exit_with_summary(
            result="fail",
            reasons=reasons,
            statuses=statuses,
            url_configured=True,
            source_type="url",
        )

    print("[slo-burn-rate-gate] result: pass")
    return _exit_with_summary(
        result="pass",
        reasons=[],
        statuses=statuses,
        url_configured=True,
        source_type="url",
    )


if __name__ == "__main__":
    sys.exit(main())
