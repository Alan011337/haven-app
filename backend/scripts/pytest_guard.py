#!/usr/bin/env python3
"""Run pytest with hard timeout guard to prevent silent hangs."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=900,
        help="Hard timeout for pytest process (default: 900s).",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=int,
        default=30,
        help="Heartbeat interval while pytest is running (default: 30s). Set 0 to disable.",
    )
    parser.add_argument(
        "--graceful-terminate-seconds",
        type=int,
        default=5,
        help="Grace period after SIGTERM before SIGKILL on timeout (default: 5s).",
    )
    parser.add_argument(
        "--step-name",
        default="pytest",
        help="Display name for timeout/heartbeat logs.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to pytest (prefix with --).",
    )
    return parser.parse_args(argv)


def _terminate_process_tree(process: subprocess.Popen[bytes], *, grace_seconds: int) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except Exception:
        return

    deadline = time.monotonic() + max(1, int(grace_seconds))
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.1)

    if process.poll() is not None:
        return

    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except Exception:
        return


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    forwarded = list(args.pytest_args or [])
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]

    command = [sys.executable, "-m", "pytest", *forwarded]
    timeout_seconds = max(1, int(args.timeout_seconds))
    heartbeat_seconds = max(0, int(args.heartbeat_seconds))
    graceful_terminate_seconds = max(1, int(args.graceful_terminate_seconds))
    step_name = str(args.step_name or "pytest")
    started = time.monotonic()
    popen_kwargs: dict[str, object] = {"cwd": os.getcwd()}
    if os.name == "posix":
        popen_kwargs["preexec_fn"] = os.setsid

    process = subprocess.Popen(command, **popen_kwargs)
    next_heartbeat = started + heartbeat_seconds if heartbeat_seconds > 0 else float("inf")
    deadline = started + timeout_seconds

    while True:
        return_code = process.poll()
        if return_code is not None:
            elapsed = int(time.monotonic() - started)
            print(
                f"[pytest-guard] completed step={step_name} exit_code={return_code} elapsed_seconds={elapsed}"
            )
            return int(return_code)

        now = time.monotonic()
        if now >= deadline:
            elapsed = int(now - started)
            print(
                f"[pytest-guard] timeout: step={step_name} exceeded {timeout_seconds}s (elapsed={elapsed}s)",
                file=sys.stderr,
            )
            _terminate_process_tree(process, grace_seconds=graceful_terminate_seconds)
            return 124

        if now >= next_heartbeat:
            elapsed = int(now - started)
            print(
                f"[pytest-guard] heartbeat step={step_name} elapsed_seconds={elapsed}",
                file=sys.stderr,
            )
            next_heartbeat = now + heartbeat_seconds

        time.sleep(0.2)


if __name__ == "__main__":
    raise SystemExit(main())
