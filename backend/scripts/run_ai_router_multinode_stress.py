#!/usr/bin/env python3
"""Run repeated AI router reliability tests under shared-state modes."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts._subprocess_utils import run_command_with_timeout

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument(
        "--modes",
        default="memory,redis",
        help="Comma-separated shared state modes to exercise.",
    )
    parser.add_argument("--output", default="/tmp/ai-router-multinode-stress-summary.json")
    parser.add_argument("--allow-failures", action="store_true")
    return parser


def _run_once(mode: str, run_index: int, timeout_seconds: int) -> dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONPATH", ".")
    env["AI_ROUTER_SHARED_STATE_BACKEND"] = mode
    cmd = [
        sys.executable,
        str(BACKEND_ROOT / "scripts" / "pytest_guard.py"),
        "--timeout-seconds",
        str(max(1, int(timeout_seconds))),
        "--heartbeat-seconds",
        "30",
        "--step-name",
        f"ai_router_multinode_{mode}_run{run_index}",
        "--",
        "-q",
        "-p",
        "no:cacheprovider",
        "tests/test_ai_provider_fallback_integration.py",
        "tests/test_ai_router_degraded_chaos.py",
        "tests/test_ai_quality_monitor.py",
    ]
    completed = run_command_with_timeout(
        command=cmd,
        cwd=BACKEND_ROOT,
        env=env,
        timeout_seconds=max(1, int(timeout_seconds)) + 10,
    )
    return {
        "mode": mode,
        "run_index": run_index,
        "exit_code": int(completed["exit_code"]),
        "stdout_tail": str(completed.get("stdout", "")),
        "stderr_tail": str(completed.get("stderr", "")),
        "timeout": bool(completed.get("timeout", False)),
    }


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    output_path = Path(args.output).resolve()
    modes = [part.strip() for part in str(args.modes).split(",") if part.strip()]
    runs = max(1, int(args.runs))

    results: list[dict[str, Any]] = []
    failed = 0
    for mode in modes:
        for run_index in range(1, runs + 1):
            item = _run_once(mode=mode, run_index=run_index, timeout_seconds=args.timeout_seconds)
            if item["exit_code"] != 0:
                failed += 1
            results.append(item)

    payload = {
        "artifact_kind": "ai-router-multinode-stress",
        "schema_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": "pass" if failed == 0 else ("degraded" if args.allow_failures else "fail"),
        "meta": {
            "runs": runs,
            "modes": modes,
            "total_executions": len(results),
            "failed_executions": failed,
            "allow_failures": bool(args.allow_failures),
        },
        "executions": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "[ai-router-multinode-stress] result={result} total={total} failed={failed} output={output}".format(
            result=payload["result"],
            total=len(results),
            failed=failed,
            output=output_path,
        )
    )
    if failed and not args.allow_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
