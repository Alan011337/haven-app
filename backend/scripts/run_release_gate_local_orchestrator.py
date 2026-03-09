#!/usr/bin/env python3
"""Structured wrapper for scripts/release-gate-local.sh.

This keeps the existing shell entrypoint intact while producing a machine-readable
summary for dashboards and CI annotations.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary-path",
        default="/tmp/release-gate-local-orchestrator-summary.json",
        help="Where to write orchestration summary JSON.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Force RELEASE_GATE_STRICT_MODE=1 for this run.",
    )
    parser.add_argument(
        "--allow-e2e-skip",
        action="store_true",
        help="Set RELEASE_GATE_ALLOW_SKIP_E2E_STRICT=1 for emergency local runs.",
    )
    parser.add_argument(
        "--release-gate-command",
        default=os.environ.get(
            "RELEASE_GATE_LOCAL_COMMAND",
            f"bash {REPO_ROOT / 'scripts' / 'release-gate-local.sh'}",
        ),
        help="Command to execute release gate (default: scripts/release-gate-local.sh).",
    )
    return parser


def _write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    summary_path = Path(args.summary_path).resolve()

    env = dict(os.environ)
    if args.strict:
        env["RELEASE_GATE_STRICT_MODE"] = "1"
    if args.allow_e2e_skip:
        env["RELEASE_GATE_ALLOW_SKIP_E2E_STRICT"] = "1"

    cmd = shlex.split(args.release_gate_command)
    started = monotonic()
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    duration_seconds = round(monotonic() - started, 3)
    result = "pass" if completed.returncode == 0 else "fail"
    reasons: list[str] = []
    if completed.returncode != 0:
        reasons.append("release_gate_failed")

    payload = {
        "artifact_kind": "release-gate-local-orchestrator",
        "schema_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "reasons": reasons,
        "meta": {
            "command": cmd,
            "returncode": int(completed.returncode),
            "duration_seconds": duration_seconds,
            "strict_mode": env.get("RELEASE_GATE_STRICT_MODE", "auto"),
            "allow_skip_e2e_strict": env.get("RELEASE_GATE_ALLOW_SKIP_E2E_STRICT", "0"),
        },
        "stdout_tail": (completed.stdout or "")[-6000:],
        "stderr_tail": (completed.stderr or "")[-6000:],
    }
    _write_summary(summary_path, payload)
    print(
        f"[release-gate-local-orchestrator] result={result} returncode={completed.returncode} "
        f"duration_s={duration_seconds} summary={summary_path}"
    )
    if completed.returncode != 0:
        return int(completed.returncode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
