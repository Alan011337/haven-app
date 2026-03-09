#!/usr/bin/env python3
"""Persist AI router runtime snapshot for trend tracking."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--health-slo-file", default="")
    parser.add_argument("--health-slo-url", default="http://127.0.0.1:8000/health/slo")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--output", default="/tmp/ai-router-runtime-snapshot.json")
    parser.add_argument("--allow-missing-source", action="store_true")
    return parser


def _load_payload_from_file(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError("payload root must be object")


def _load_payload_from_url(*, url: str, timeout_seconds: float) -> dict[str, Any]:
    req = request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with request.urlopen(req, timeout=timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("payload root must be object")
    return payload


def _load_payload(*, path: str, url: str, timeout_seconds: float) -> tuple[dict[str, Any], str]:
    errors_seen: list[tuple[str, Exception]] = []
    if path:
        try:
            return _load_payload_from_file(path), "file"
        except (OSError, ValueError, json.JSONDecodeError) as exc:  # pragma: no cover - tested via main
            errors_seen.append(("file", exc))
    try:
        return _load_payload_from_url(url=url, timeout_seconds=timeout_seconds), "url"
    except (error.URLError, error.HTTPError, ValueError, json.JSONDecodeError, OSError) as exc:
        errors_seen.append(("url", exc))

    if errors_seen:
        # Prefer file-side failure when explicit path is provided so callers can troubleshoot quickly.
        if path:
            source, exc = errors_seen[0]
            raise RuntimeError(f"{source}_source_unavailable:{type(exc).__name__}") from exc
        source, exc = errors_seen[-1]
        raise RuntimeError(f"{source}_source_unavailable:{type(exc).__name__}") from exc
    raise RuntimeError("source_unavailable")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        payload, source = _load_payload(
            path=args.health_slo_file,
            url=args.health_slo_url,
            timeout_seconds=args.timeout_seconds,
        )
    except RuntimeError as exc:
        if args.allow_missing_source:
            error_label = str(exc).split(":", 1)[0] or "source_unavailable"
            summary = {
                "artifact_kind": "ai-router-runtime-snapshot",
                "schema_version": "v1",
                "result": "skipped",
                "reasons": [error_label],
                "meta": {"error_type": type(exc).__name__},
            }
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(summary, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
            print(f"[ai-router-runtime-persist] result=skipped reason={error_label} output={out}")
            return 0
        print(f"[ai-router-runtime-persist] fail: {exc}")
        return 1

    sli = payload.get("sli") if isinstance(payload.get("sli"), dict) else {}
    runtime = sli.get("ai_router_runtime") if isinstance(sli.get("ai_router_runtime"), dict) else {}
    evaluation = runtime.get("evaluation") if isinstance(runtime.get("evaluation"), dict) else {}
    state = runtime.get("state") if isinstance(runtime.get("state"), dict) else {}
    counters = runtime.get("counters") if isinstance(runtime.get("counters"), dict) else {}
    result = "pass"
    reasons: list[str] = []
    if not runtime:
        result = "degraded"
        reasons.append("ai_router_runtime_missing")

    snapshot = {
        "artifact_kind": "ai-router-runtime-snapshot",
        "schema_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "reasons": reasons,
        "runtime": {
            "evaluation": evaluation,
            "state": state,
            "counters": counters,
        },
        "meta": {"source": source},
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "[ai-router-runtime-persist] result={result} reasons={reasons} output={output}".format(
            result=result,
            reasons="none" if not reasons else ",".join(reasons),
            output=out,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
