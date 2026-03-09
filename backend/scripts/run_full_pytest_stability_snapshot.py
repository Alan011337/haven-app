#!/usr/bin/env python3
"""Run (or dry-run) full pytest stability snapshot with timeout guard."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Execute full pytest through pytest_guard.")
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--output", default="/tmp/full-pytest-stability-summary.json")
    parser.add_argument(
        "--pytest-args",
        default="-q -p no:cacheprovider",
        help="Forwarded arguments to pytest (string form).",
    )
    return parser


def _write_output(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    output_path = Path(args.output).resolve()
    timeout_seconds = max(60, int(args.timeout_seconds))
    started = time.time()

    if not args.run:
        payload = {
            "artifact_kind": "full-pytest-stability-snapshot",
            "schema_version": "v1",
            "result": "skipped",
            "reasons": ["run_disabled"],
            "meta": {
                "timeout_seconds": timeout_seconds,
                "pytest_args": args.pytest_args,
            },
        }
        _write_output(output_path, payload)
        print(f"[full-pytest-stability] result=skipped output={output_path}")
        return 0

    forwarded_args = [part for part in args.pytest_args.strip().split(" ") if part]
    cmd = [
        sys.executable,
        str(BACKEND_ROOT / "scripts" / "pytest_guard.py"),
        "--timeout-seconds",
        str(timeout_seconds),
        "--",
        *forwarded_args,
    ]
    completed = subprocess.run(cmd, cwd=str(BACKEND_ROOT), capture_output=True, text=True, check=False)  # noqa: S603
    elapsed = max(0.0, time.time() - started)
    result = "pass" if completed.returncode == 0 else "fail"
    reasons: list[str] = []
    if completed.returncode == 124:
        reasons.append("pytest_timeout")
    elif completed.returncode != 0:
        reasons.append("pytest_failed")

    payload = {
        "artifact_kind": "full-pytest-stability-snapshot",
        "schema_version": "v1",
        "result": result,
        "reasons": reasons,
        "meta": {
            "timeout_seconds": timeout_seconds,
            "pytest_args": args.pytest_args,
            "elapsed_seconds": round(elapsed, 3),
            "exit_code": int(completed.returncode),
            "stdout_tail": (completed.stdout or "")[-4000:],
            "stderr_tail": (completed.stderr or "")[-4000:],
        },
    }
    _write_output(output_path, payload)
    print(
        f"[full-pytest-stability] result={result} exit_code={completed.returncode} "
        f"elapsed_seconds={payload['meta']['elapsed_seconds']} output={output_path}"
    )
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
