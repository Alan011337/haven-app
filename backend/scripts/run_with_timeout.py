#!/usr/bin/env python3
"""Run any command with hard timeout and optional heartbeat logs."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from typing import Sequence


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--heartbeat-seconds", type=int, default=30)
    parser.add_argument("--step-name", default="gate_step")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser.parse_args(list(argv))


def _terminate_process_tree(process: subprocess.Popen[bytes], *, grace_seconds: int = 5) -> None:
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


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("[run-with-timeout] fail: missing command", file=sys.stderr)
        return 2

    timeout_seconds = max(1, int(args.timeout_seconds))
    heartbeat_seconds = max(0, int(args.heartbeat_seconds))
    started = time.monotonic()
    print(
        f"[run-with-timeout] start step={args.step_name} timeout_seconds={timeout_seconds} "
        f"command={' '.join(command)}"
    )

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
                f"[run-with-timeout] done step={args.step_name} exit_code={return_code} elapsed_seconds={elapsed}"
            )
            return int(return_code)

        now = time.monotonic()
        if now >= deadline:
            elapsed = int(now - started)
            print(
                f"[run-with-timeout] timeout step={args.step_name} elapsed_seconds={elapsed}",
                file=sys.stderr,
            )
            _terminate_process_tree(process)
            return 124

        if now >= next_heartbeat:
            elapsed = int(now - started)
            print(
                f"[run-with-timeout] heartbeat step={args.step_name} elapsed_seconds={elapsed}"
            )
            next_heartbeat = now + heartbeat_seconds

        time.sleep(0.2)


if __name__ == "__main__":
    raise SystemExit(main())
