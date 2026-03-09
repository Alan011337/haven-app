#!/usr/bin/env python3
"""Run data retention bundle (events_log + soft-delete purge) with safe defaults."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts._subprocess_utils import run_command_with_timeout

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Execute apply mode for both retention jobs.")
    parser.add_argument(
        "--output",
        default="/tmp/data-retention-bundle-summary.json",
        help="Output summary JSON path.",
    )
    parser.add_argument(
        "--allow-job-failures",
        action="store_true",
        help="Return success even when one sub-job fails (result becomes degraded).",
    )
    parser.add_argument(
        "--job-timeout-seconds",
        type=int,
        default=20,
        help="Per-subjob timeout in seconds (default: 20).",
    )
    parser.add_argument(
        "--degrade-timeout-in-dry-run",
        action="store_true",
        help="Treat timeout-only failures as degraded in dry-run mode even without --allow-job-failures.",
    )
    return parser


def _run_command(command: list[str], *, timeout_seconds: int) -> dict[str, Any]:
    result = run_command_with_timeout(
        command=command,
        cwd=BACKEND_ROOT,
        timeout_seconds=timeout_seconds,
    )
    stdout = result["stdout"]
    stderr = result["stderr"]
    parsed: dict[str, Any] | None = None
    if stdout.startswith("{") and stdout.endswith("}"):
        try:
            payload = json.loads(stdout)
            if isinstance(payload, dict):
                parsed = payload
        except json.JSONDecodeError:
            parsed = None
    return {
        "exit_code": int(result["exit_code"]),
        "stdout": stdout,
        "stderr": stderr,
        "payload": parsed,
        "timeout": bool(result["timeout"]),
    }


def _classify_failure(job_result: dict[str, Any]) -> str:
    if int(job_result.get("exit_code", 1)) == 0:
        return "none"
    if bool(job_result.get("timeout")):
        return "job_timeout"
    payload = job_result.get("payload")
    if isinstance(payload, dict) and str(payload.get("result", "")).strip().lower() in {
        "fail",
        "degraded",
        "error",
    }:
        return "job_reported_failure"
    return "job_exit_nonzero"


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    mode = "apply" if args.apply else "dry_run"

    events_cmd = [sys.executable, "scripts/run_events_log_retention.py"]
    purge_cmd = [sys.executable, "scripts/run_data_soft_delete_purge.py"]
    if args.apply:
        events_cmd.extend(["--apply", "--confirm-apply", "events-log-retention-apply"])
        purge_cmd.append("--apply")

    job_timeout_seconds = max(1, int(args.job_timeout_seconds))
    events_result = _run_command(events_cmd, timeout_seconds=job_timeout_seconds)
    purge_result = _run_command(purge_cmd, timeout_seconds=job_timeout_seconds)
    jobs = {
        "events_log_retention": events_result,
        "soft_delete_purge": purge_result,
    }
    failure_classes: dict[str, str] = {}
    failures: list[str] = []
    for job_name, job_result in jobs.items():
        failure_class = _classify_failure(job_result)
        job_result["failure_class"] = failure_class
        failure_classes[job_name] = failure_class
        if int(job_result["exit_code"]) != 0:
            if job_name == "events_log_retention":
                failures.append("events_log_retention_failed")
            elif job_name == "soft_delete_purge":
                failures.append("soft_delete_purge_failed")

    timeout_only_failure = bool(failures) and all(
        failure_classes.get(job_name, "") == "job_timeout"
        for job_name, job_result in jobs.items()
        if int(job_result["exit_code"]) != 0
    )

    result = "pass" if not failures else "degraded"
    if failures and not args.allow_job_failures:
        if mode == "dry_run" and args.degrade_timeout_in_dry_run and timeout_only_failure:
            result = "degraded"
        else:
            result = "fail"

    payload = {
        "artifact_kind": "data-retention-bundle",
        "schema_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "result": result,
        "reasons": failures,
        "failure_classes": sorted(
            {
                failure_class
                for failure_class in failure_classes.values()
                if failure_class and failure_class != "none"
            }
        ),
        "meta": {
            "allow_job_failures": bool(args.allow_job_failures),
            "degrade_timeout_in_dry_run": bool(args.degrade_timeout_in_dry_run),
            "job_timeout_seconds": job_timeout_seconds,
            "timeout_only_failure": timeout_only_failure,
        },
        "jobs": {
            "events_log_retention": jobs["events_log_retention"],
            "soft_delete_purge": jobs["soft_delete_purge"],
        },
    }
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"[data-retention-bundle] mode={mode} result={result} reasons="
        f"{'none' if not failures else ','.join(failures)} output={output_path}"
    )
    if result == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
