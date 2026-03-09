#!/usr/bin/env python3
"""Production-safe CUJ synthetic skeleton for Haven."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request
from urllib.parse import urljoin, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "sre" / "evidence"
BASE_URL_ENV_KEY = "SYNTHETIC_BASE_URL"
TOKEN_ENV_KEY = "SYNTHETIC_BEARER_TOKEN"
TIMEOUT_ENV_KEY = "SYNTHETIC_TIMEOUT_SECONDS"
DEFAULT_TIMEOUT_SECONDS = 10.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_timeout(raw: str | None) -> float:
    if raw is None or str(raw).strip() == "":
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError("timeout must be a number") from exc
    if value <= 0:
        raise ValueError("timeout must be greater than 0")
    return value


def _validate_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("base-url must start with http:// or https://")
    if not parsed.netloc:
        raise ValueError("base-url must include host")
    return base_url.rstrip("/")


def _fetch_json(*, url: str, timeout_seconds: float, bearer_token: str | None) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    req = request.Request(url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            status_code = int(getattr(response, "status", response.getcode()))
            payload_text = response.read().decode("utf-8")
    except error.HTTPError as exc:
        payload_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {payload_text}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"request failed: {exc}") from exc

    if status_code >= 400:
        raise RuntimeError(f"HTTP {status_code}: {payload_text}")

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("endpoint response is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("endpoint JSON root must be object")
    return payload


def _load_payload_file(*, path: Path, label: str) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(f"{label} payload file not found: {path}") from exc
    except OSError as exc:
        raise RuntimeError(f"unable to read {label} payload file: {path}: {exc}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} payload file is not valid JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} payload root must be object: {path}")
    return payload


def evaluate_cuj_synthetic(
    *,
    health_payload: dict[str, Any],
    slo_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool]:
    stages: list[dict[str, Any]] = []

    health_status = str(health_payload.get("status") or "unknown").lower()
    health_ok = health_status == "ok"
    stages.append(
        {
            "stage": "health_endpoint",
            "status": "pass" if health_ok else "fail",
            "detail": f"health.status={health_status}",
        }
    )

    evaluation = (slo_payload.get("sli") or {}).get("evaluation")
    ws_status = "missing"
    ws_burn_rate_status = "missing"
    cuj_status = "missing"
    if isinstance(evaluation, dict):
        ws_status = str((evaluation.get("ws") or {}).get("status") or "missing").lower()
        ws_burn_rate_status = str(
            (evaluation.get("ws_burn_rate") or {}).get("status") or "missing"
        ).lower()
        cuj_status = str((evaluation.get("cuj") or {}).get("status") or "missing").lower()
    if cuj_status == "missing":
        cuj_status = "insufficient_data"

    ws_gate_ok = ws_status in {"ok", "insufficient_data"} and ws_burn_rate_status in {
        "ok",
        "insufficient_data",
    }
    ws_stage_status = "pass" if ws_gate_ok else "fail"
    stages.append(
        {
            "stage": "ws_slo_gate",
            "status": ws_stage_status,
            "detail": f"ws={ws_status}, ws_burn_rate={ws_burn_rate_status}",
        }
    )

    cuj_gate_ok = cuj_status in {"ok", "insufficient_data"}
    stages.append(
        {
            "stage": "cuj_slo_gate",
            "status": "pass" if cuj_gate_ok else "fail",
            "detail": f"cuj={cuj_status}",
        }
    )

    ritual_status = "pass" if ws_status == "ok" else "warn"
    stages.append(
        {
            "stage": "cuj_01_ritual",
            "status": ritual_status,
            "detail": "skeleton probe uses /health/slo ws status as proxy",
        }
    )

    sli_payload = health_payload.get("sli")
    http_observability = None
    if isinstance(sli_payload, dict):
        http_observability = sli_payload.get("http_runtime")
    if not isinstance(http_observability, dict):
        # Backward compatibility for older health payload schema.
        http_observability = health_payload.get("http_observability")
    journal_status = "warn"
    journal_detail = "missing_http_observability"
    if isinstance(http_observability, dict):
        sample_count = int(http_observability.get("sample_count", 0) or 0)
        p95 = ((http_observability.get("latency_ms") or {}).get("p95", 0.0))
        if sample_count > 0:
            journal_status = "pass" if float(p95) < 4000.0 else "fail"
            journal_detail = f"sample_count={sample_count}, p95_ms={p95}"
        else:
            journal_detail = "sample_count=0"
    stages.append(
        {
            "stage": "cuj_02_journal",
            "status": journal_status,
            "detail": journal_detail,
        }
    )

    hard_fail = any(stage["status"] == "fail" for stage in stages)
    return stages, not hard_fail


def classify_synthetic_failure(stages: list[dict[str, Any]]) -> str:
    failed_stages = {str(stage.get("stage")) for stage in stages if stage.get("status") == "fail"}
    if not failed_stages:
        return "none"
    if "health_endpoint" in failed_stages:
        return "health_endpoint_unavailable"
    if "ws_slo_gate" in failed_stages:
        return "ws_slo_degraded"
    if "cuj_slo_gate" in failed_stages:
        return "cuj_slo_degraded"
    if "cuj_02_journal" in failed_stages:
        return "journal_latency_regression"
    return "synthetic_stage_failure"


def _write_evidence(*, output_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    json_path = output_dir / f"cuj-synthetic-{stamp}.json"
    md_path = output_dir / f"cuj-synthetic-{stamp}.md"

    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    lines = [
        "# CUJ Synthetic Probe",
        "",
        f"- Generated at (UTC): {payload.get('generated_at')}",
        f"- Base URL: {payload.get('base_url')}",
        f"- Result: {payload.get('result')}",
        "",
        "| Stage | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for stage in payload.get("stages", []):
        lines.append(
            f"| `{stage.get('stage')}` | `{stage.get('status')}` | {stage.get('detail')} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def _write_summary(*, summary_path: str | None, payload: dict[str, Any]) -> None:
    if not summary_path:
        return
    path = Path(summary_path)
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Haven CUJ synthetic skeleton against /health and /health/slo"
    )
    parser.add_argument("--base-url", default=None, help=f"Target base URL (defaults to ${BASE_URL_ENV_KEY})")
    parser.add_argument("--bearer-token", default=None, help=f"Auth token (defaults to ${TOKEN_ENV_KEY})")
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--allow-missing-url", action="store_true")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--health-payload-file",
        default=None,
        help="Optional local health payload JSON file (offline mode; requires --slo-payload-file).",
    )
    parser.add_argument(
        "--slo-payload-file",
        default=None,
        help="Optional local health/slo payload JSON file (offline mode; requires --health-payload-file).",
    )
    parser.add_argument("--strict", action="store_true", help="Treat warn stages as failure")
    parser.add_argument(
        "--summary-path",
        default=None,
        help="Optional JSON summary output for CI step summaries and alert routing.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    raw_base_url = (args.base_url or os.getenv(BASE_URL_ENV_KEY, "")).strip()
    bearer_token = (args.bearer_token or os.getenv(TOKEN_ENV_KEY, "")).strip() or None
    health_payload_file = (args.health_payload_file or "").strip()
    slo_payload_file = (args.slo_payload_file or "").strip()
    offline_mode = bool(health_payload_file or slo_payload_file)

    if offline_mode and not (health_payload_file and slo_payload_file):
        print("[cuj-synthetics] fail: offline payload arguments must be provided as a pair")
        print("  required: --health-payload-file + --slo-payload-file")
        return 1

    if not offline_mode and not raw_base_url:
        if args.allow_missing_url:
            print("[cuj-synthetics] skipped: missing base URL")
            print(f"  set {BASE_URL_ENV_KEY} or pass --base-url")
            return 0
        print("[cuj-synthetics] fail: missing base URL")
        print(f"  required: {BASE_URL_ENV_KEY} or --base-url")
        return 1

    base_url = "offline_fixture://health" if offline_mode else raw_base_url
    timeout_seconds = DEFAULT_TIMEOUT_SECONDS
    if not offline_mode:
        try:
            base_url = _validate_base_url(raw_base_url)
            timeout_seconds = (
                float(args.timeout_seconds)
                if args.timeout_seconds is not None
                else _parse_timeout(os.getenv(TIMEOUT_ENV_KEY))
            )
        except ValueError as exc:
            print("[cuj-synthetics] fail: invalid argument")
            print(f"  detail: {exc}")
            return 1

    print("[cuj-synthetics] running")
    print(f"  base_url: {base_url}")
    print(f"  timeout_seconds: {timeout_seconds}")

    if offline_mode:
        print("[cuj-synthetics] mode: offline payload files")
        print(f"  health_payload_file: {health_payload_file}")
        print(f"  slo_payload_file: {slo_payload_file}")
        try:
            health_payload = _load_payload_file(
                path=Path(health_payload_file),
                label="health",
            )
            slo_payload = _load_payload_file(
                path=Path(slo_payload_file),
                label="slo",
            )
        except RuntimeError as exc:
            print("[cuj-synthetics] fail: payload file error")
            print(f"  detail: {exc}")
            return 1
    else:
        health_url = urljoin(base_url + "/", "health")
        slo_url = urljoin(base_url + "/", "health/slo")
        try:
            health_payload = _fetch_json(
                url=health_url,
                timeout_seconds=timeout_seconds,
                bearer_token=bearer_token,
            )
            slo_payload = _fetch_json(
                url=slo_url,
                timeout_seconds=timeout_seconds,
                bearer_token=bearer_token,
            )
        except RuntimeError as exc:
            print("[cuj-synthetics] fail: request error")
            print(f"  detail: {exc}")
            return 1

    stages, passed = evaluate_cuj_synthetic(health_payload=health_payload, slo_payload=slo_payload)
    if args.strict:
        if any(stage.get("status") == "warn" for stage in stages):
            passed = False
    failure_class = classify_synthetic_failure(stages)
    failed_stage_names = [str(stage.get("stage")) for stage in stages if stage.get("status") == "fail"]
    warn_stage_names = [str(stage.get("stage")) for stage in stages if stage.get("status") == "warn"]

    result_payload = {
        "generated_at": _utc_now_iso(),
        "base_url": base_url,
        "result": "pass" if passed else "fail",
        "failure_class": failure_class,
        "failed_stages": failed_stage_names,
        "warn_stages": warn_stage_names,
        "strict_mode": bool(args.strict),
        "stages": stages,
    }
    json_path, md_path = _write_evidence(output_dir=Path(args.output_dir), payload=result_payload)
    _write_summary(
        summary_path=(args.summary_path or "").strip() or None,
        payload={
            "result": result_payload["result"],
            "failure_class": failure_class,
            "failed_stages": failed_stage_names,
            "warn_stages": warn_stage_names,
            "strict_mode": bool(args.strict),
            "base_url": base_url,
        },
    )

    print(f"  evidence_json: {json_path}")
    print(f"  evidence_md: {md_path}")
    print(f"  failure_class: {failure_class}")
    print(f"[cuj-synthetics] result: {'pass' if passed else 'fail'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
