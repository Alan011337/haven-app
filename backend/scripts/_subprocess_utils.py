#!/usr/bin/env python3
"""Shared subprocess helpers for backend scripts."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def run_command_with_timeout(
    *,
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    env: dict[str, str] | None = None,
    stdout_truncate: int = 4000,
    stderr_truncate: int = 4000,
) -> dict[str, Any]:
    timeout = max(1, int(timeout_seconds))
    try:
        completed = subprocess.run(  # noqa: S603
            command,
            cwd=str(cwd),
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "").strip() if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "").strip() if isinstance(exc.stderr, str) else ""
        return {
            "exit_code": 124,
            "stdout": stdout[-stdout_truncate:],
            "stderr": (stderr[-max(0, stderr_truncate - 32) :] + f"\nsubjob_timeout={timeout}s").strip(),
            "timeout": True,
        }

    return {
        "exit_code": int(completed.returncode),
        "stdout": (completed.stdout or "").strip()[-stdout_truncate:],
        "stderr": (completed.stderr or "").strip()[-stderr_truncate:],
        "timeout": False,
    }
