#!/usr/bin/env python3
"""Aggregate gate component summaries into one orchestration JSON payload."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

PASS_RESULTS = {"pass", "ok", "ready", "accepted"}
DEGRADED_RESULTS = {"degraded", "warning", "insufficient_data", "unavailable"}
FAIL_RESULTS = {"fail", "error", "blocked", "rejected"}


def _parse_component(raw: str) -> tuple[str, Path, bool]:
    parts = [segment.strip() for segment in raw.split(",")]
    if len(parts) not in {2, 3}:
        raise argparse.ArgumentTypeError(
            "component must follow '<name>,<path>[,required|optional]'"
        )
    name = parts[0].strip().lower()
    path = Path(parts[1]).expanduser()
    required = True
    if len(parts) == 3:
        token = parts[2].strip().lower()
        if token not in {"required", "optional"}:
            raise argparse.ArgumentTypeError("component mode must be required|optional")
        required = token == "required"
    if not name:
        raise argparse.ArgumentTypeError("component name must be non-empty")
    return name, path, required


def _parse_metadata(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("metadata must follow key=value")
    key, value = raw.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        raise argparse.ArgumentTypeError("metadata key must be non-empty")
    return key, value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", default="release", help="release | release-local | custom")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument(
        "--component",
        action="append",
        default=[],
        help="Component descriptor: '<name>,<path>[,required|optional]'",
    )
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        help="Additional metadata as key=value.",
    )
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="Exit non-zero unless overall_result is pass.",
    )
    return parser


def _normalize_result(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in PASS_RESULTS:
        return "pass"
    if normalized in DEGRADED_RESULTS:
        return "degraded"
    if normalized in FAIL_RESULTS:
        return "fail"
    return "unknown"


def _component_payload(*, name: str, path: Path, required: bool) -> dict:
    payload = {
        "name": name,
        "path": str(path),
        "required": required,
        "result": "unknown",
        "source_result": "missing",
        "reasons": [],
    }
    if not path.exists():
        if required:
            payload["result"] = "degraded"
            payload["reasons"] = ["required_summary_missing"]
        else:
            payload["result"] = "pass"
            payload["source_result"] = "skipped_optional"
            payload["reasons"] = ["optional_summary_missing"]
        return payload

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload["result"] = "fail"
        payload["source_result"] = "parse_error"
        payload["reasons"] = ["summary_parse_error"]
        return payload

    if not isinstance(data, dict):
        payload["result"] = "fail"
        payload["source_result"] = "invalid_shape"
        payload["reasons"] = ["summary_invalid_shape"]
        return payload

    source_result = str(data.get("result", "unknown"))
    payload["source_result"] = source_result
    payload["result"] = _normalize_result(source_result)
    reasons = data.get("reasons")
    if isinstance(reasons, list):
        payload["reasons"] = [str(reason) for reason in reasons[:10]]
    elif reasons:
        payload["reasons"] = [str(reasons)]
    else:
        payload["reasons"] = []
    return payload


def _overall_result(components: list[dict]) -> str:
    if any(component.get("result") == "fail" for component in components):
        return "fail"
    if any(component.get("result") == "degraded" for component in components):
        return "degraded"
    if any(component.get("result") == "unknown" for component in components):
        return "degraded"
    return "pass"


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    components: list[dict] = []
    for raw in args.component:
        name, path, required = _parse_component(raw)
        components.append(_component_payload(name=name, path=path, required=required))

    metadata: dict[str, str] = {}
    for raw in args.metadata:
        key, value = _parse_metadata(raw)
        metadata[key] = value

    payload = {
        "schema_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": str(args.mode),
        "overall_result": _overall_result(components),
        "components": components,
        "metadata": metadata,
    }

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "[gate-orchestration] summary result=%s components=%s output=%s"
        % (payload["overall_result"], len(components), output_path)
    )

    if args.require_pass and payload["overall_result"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
