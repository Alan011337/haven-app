#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_URL = "sqlite:////tmp/haven-alembic-rehearsal.db"
DEFAULT_REPORT_PATH = "/tmp/haven-alembic-rehearsal-report.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run alembic migration rehearsal and emit JSON report.")
    parser.add_argument("--database-url", default=DEFAULT_DB_URL, help="Target DATABASE_URL for rehearsal.")
    parser.add_argument("--report-path", default=DEFAULT_REPORT_PATH, help="Output JSON report path.")
    parser.add_argument(
        "--python-bin",
        default=os.getenv("BACKEND_PYTHON_BIN", str(BACKEND_DIR / ".venv-gate" / "bin" / "python")),
        help="Python executable for bootstrap/alembic commands.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit report without executing commands.",
    )
    return parser.parse_args()


def _command_steps(python_bin: str) -> list[tuple[str, list[str]]]:
    return [
        ("bootstrap_sqlite_schema", [python_bin, "scripts/bootstrap-sqlite-schema.py"]),
        ("verify_only", ["./scripts/run-alembic.sh", "--mode", "verify-only"]),
        ("upgrade_head_1", ["./scripts/run-alembic.sh", "upgrade", "head"]),
        ("downgrade_baseline", ["./scripts/run-alembic.sh", "downgrade", "h1core0000011"]),
        ("upgrade_head_2", ["./scripts/run-alembic.sh", "upgrade", "head"]),
    ]


def _run_step(*, name: str, command: list[str], env: dict[str, str]) -> dict[str, Any]:
    started = time.time()
    process = subprocess.run(
        command,
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    duration_seconds = round(time.time() - started, 3)
    return {
        "name": name,
        "command": " ".join(shlex.quote(part) for part in command),
        "exit_code": int(process.returncode),
        "duration_seconds": duration_seconds,
        "stdout_tail": process.stdout.splitlines()[-10:],
        "stderr_tail": process.stderr.splitlines()[-10:],
        "status": "pass" if process.returncode == 0 else "fail",
    }


def _write_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    report_path = Path(args.report_path).expanduser().resolve()

    env = os.environ.copy()
    env["DATABASE_URL"] = args.database_url
    env["PYTHONUTF8"] = "1"
    env["PYTHONPATH"] = f"{BACKEND_DIR}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    env["BACKEND_PYTHON_BIN"] = args.python_bin

    steps_def = _command_steps(args.python_bin)
    if args.dry_run:
        report = {
            "artifact_kind": "migration-rehearsal-report",
            "schema_version": "v1",
            "status": "dry_run",
            "database_url": args.database_url,
            "steps": [
                {
                    "name": name,
                    "command": " ".join(shlex.quote(part) for part in command),
                    "status": "planned",
                }
                for name, command in steps_def
            ],
        }
        _write_report(report_path, report)
        print(f"[migration-rehearsal] dry-run report written: {report_path}")
        return 0

    steps: list[dict[str, Any]] = []
    overall_status = "pass"
    for name, command in steps_def:
        step_report = _run_step(name=name, command=command, env=env)
        steps.append(step_report)
        if step_report["status"] != "pass":
            overall_status = "fail"
            break

    report = {
        "artifact_kind": "migration-rehearsal-report",
        "schema_version": "v1",
        "status": overall_status,
        "database_url": args.database_url,
        "steps": steps,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _write_report(report_path, report)
    print(f"[migration-rehearsal] report written: {report_path}")
    print(f"[migration-rehearsal] status: {overall_status}")
    return 0 if overall_status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
