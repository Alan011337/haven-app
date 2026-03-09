#!/usr/bin/env python3
"""Post-deploy smoke checks for core Haven flows."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ProbeResult:
    domain: str
    method: str
    path: str
    status_code: int
    ok: bool
    reason: str


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--inventory",
        default="/Users/alanzeng/Desktop/Projects/Haven/docs/security/api-inventory.json",
    )
    parser.add_argument("--output", default="/tmp/post-deploy-smoke-summary.json")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument(
        "--token-env",
        default="POST_DEPLOY_BEARER_TOKEN",
        help="Env var name for optional bearer token.",
    )
    return parser


def _load_inventory(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    if isinstance(entries, list):
        return [item for item in entries if isinstance(item, dict)]
    return []


def _pick_domain_endpoint(entries: list[dict[str, Any]], domain: str) -> tuple[str, str]:
    mapping = {
        "auth": ("/api/auth/",),
        "journal": ("/api/journals",),
        "card": ("/api/cards",),
        "memory": ("/api/memory",),
        "notification": ("/api/notifications", "/api/users/notifications"),
    }
    candidates = mapping.get(domain, ())
    for entry in entries:
        method = str(entry.get("method", "GET")).upper()
        path = str(entry.get("path", ""))
        if not path.startswith("/api/"):
            continue
        if any(token in path for token in candidates):
            return method, path
    fallback = {
        "auth": ("POST", "/api/auth/token"),
        "journal": ("GET", "/api/journals"),
        "card": ("GET", "/api/cards"),
        "memory": ("GET", "/api/memory/timeline"),
        "notification": ("GET", "/api/notifications"),
    }
    return fallback[domain]


def _request_json(
    *,
    base_url: str,
    method: str,
    path: str,
    timeout_seconds: float,
    token: str | None,
) -> tuple[int, dict[str, Any] | None]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    headers = {"Accept": "application/json"}
    body: bytes | None = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if method in {"POST", "PUT", "PATCH"}:
        headers["Content-Type"] = "application/json"
        body = b"{}"
    req = Request(url=url, method=method, headers=headers, data=body)
    try:
        with urlopen(req, timeout=timeout_seconds) as response:  # noqa: S310
            status = int(getattr(response, "status", 200))
            raw = response.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return status, None
            try:
                payload = json.loads(raw)
                if isinstance(payload, dict):
                    return status, payload
            except json.JSONDecodeError:
                return status, None
            return status, None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        payload: dict[str, Any] | None = None
        if raw.strip():
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    payload = parsed
            except json.JSONDecodeError:
                payload = None
        return int(exc.code), payload
    except URLError:
        return 0, None


def _probe_health(base_url: str, token: str | None, timeout_seconds: float) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    for path in ("/health", "/health/slo"):
        status, payload = _request_json(
            base_url=base_url,
            method="GET",
            path=path,
            timeout_seconds=timeout_seconds,
            token=token,
        )
        if status != 200:
            results.append(
                ProbeResult(
                    domain=path,
                    method="GET",
                    path=path,
                    status_code=status,
                    ok=False,
                    reason="status_not_200",
                )
            )
            continue
        if path == "/health/slo":
            sli = payload.get("sli") if isinstance(payload, dict) else {}
            checks = payload.get("checks") if isinstance(payload, dict) else {}
            required_ok = isinstance(sli, dict) and isinstance(checks, dict) and (
                "notification_runtime" in sli
                and "dynamic_content_runtime" in sli
                and "notification_outbox_depth" in checks
            )
            results.append(
                ProbeResult(
                    domain=path,
                    method="GET",
                    path=path,
                    status_code=status,
                    ok=bool(required_ok),
                    reason="ok" if required_ok else "missing_required_runtime_fields",
                )
            )
        else:
            results.append(
                ProbeResult(
                    domain=path,
                    method="GET",
                    path=path,
                    status_code=status,
                    ok=True,
                    reason="ok",
                )
            )
    return results


def _probe_domain(
    *,
    domain: str,
    method: str,
    path: str,
    base_url: str,
    timeout_seconds: float,
    token: str | None,
) -> ProbeResult:
    status, _payload = _request_json(
        base_url=base_url,
        method=method,
        path=path,
        timeout_seconds=timeout_seconds,
        token=token,
    )
    if status == 0:
        return ProbeResult(domain=domain, method=method, path=path, status_code=0, ok=False, reason="network_error")
    if status == 404:
        return ProbeResult(domain=domain, method=method, path=path, status_code=status, ok=False, reason="route_not_found")
    acceptable = {200, 201, 202, 204, 401, 403, 422}
    ok = status in acceptable
    reason = "ok" if ok else "unexpected_status"
    return ProbeResult(domain=domain, method=method, path=path, status_code=status, ok=ok, reason=reason)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    base_url = str(args.base_url).strip()
    timeout_seconds = max(1.0, float(args.timeout_seconds))
    token = os.getenv(str(args.token_env), "").strip() or None
    inventory_entries = _load_inventory(Path(args.inventory))

    probes: list[ProbeResult] = []
    probes.extend(_probe_health(base_url, token, timeout_seconds))

    for domain in ("auth", "journal", "card", "memory", "notification"):
        method, path = _pick_domain_endpoint(inventory_entries, domain)
        probes.append(
            _probe_domain(
                domain=domain,
                method=method,
                path=path,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                token=token,
            )
        )

    failed = [probe for probe in probes if not probe.ok]
    payload = {
        "artifact_kind": "post-deploy-smoke",
        "schema_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "result": "pass" if not failed else "fail",
        "probes": [
            {
                "domain": p.domain,
                "method": p.method,
                "path": p.path,
                "status_code": p.status_code,
                "ok": p.ok,
                "reason": p.reason,
            }
            for p in probes
        ],
        "failures": [
            {
                "domain": p.domain,
                "path": p.path,
                "status_code": p.status_code,
                "reason": p.reason,
            }
            for p in failed
        ],
    }

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"[post-deploy-smoke] result={payload['result']} failures={len(failed)} output={output_path}"
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
