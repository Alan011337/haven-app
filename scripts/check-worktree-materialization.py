#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import subprocess
from pathlib import Path

DEFAULT_PATHS = (
    "backend/app/main.py",
    "backend/app/services/ai_router.py",
    "backend/app/core/health_routes.py",
    "backend/app/services/notification.py",
    "backend/scripts/security-gate.sh",
    "scripts/release-gate-local.sh",
    "backend/fly.toml",
    "frontend/fly.toml",
    "frontend/src/services/api-client.ts",
    "frontend/src/hooks/useSocket.ts",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check critical repo files are materialized (not iCloud dataless).")
    parser.add_argument("--root", default=".")
    parser.add_argument("--summary-path", default="")
    parser.add_argument("--allow-dataless", action="store_true")
    parser.add_argument("paths", nargs="*", help="Optional relative paths to check.")
    return parser.parse_args()


def _write_summary(path: str, payload: dict) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def _flag_string(path: Path) -> str:
    proc = subprocess.run(["ls", "-lO", str(path)], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip().lower()


def main() -> int:
    args = _parse_args()
    root = Path(args.root).resolve()
    rel_paths = tuple(args.paths) if args.paths else DEFAULT_PATHS

    if platform.system().lower() != "darwin":
        payload = {
            "result": "skipped",
            "reasons": ["unsupported_platform"],
            "meta": {"platform": platform.system()},
        }
        _write_summary(args.summary_path, payload)
        print("[worktree-materialization] result: skipped (unsupported_platform)")
        return 0

    missing: list[str] = []
    dataless: list[str] = []

    for rel in rel_paths:
        path = (root / rel).resolve()
        if not path.exists():
            missing.append(rel)
            continue
        flags = _flag_string(path)
        if "dataless" in flags:
            dataless.append(rel)

    reasons: list[str] = []
    if missing:
        reasons.append("missing_files")
    if dataless:
        reasons.append("dataless_files")

    if reasons and args.allow_dataless:
        result = "degraded"
    elif reasons:
        result = "fail"
    else:
        result = "pass"

    payload = {
        "result": result,
        "reasons": reasons,
        "meta": {
            "root": str(root),
            "checked_total": len(rel_paths),
            "missing_total": len(missing),
            "dataless_total": len(dataless),
        },
        "missing": missing,
        "dataless": dataless,
    }
    _write_summary(args.summary_path, payload)

    print("[worktree-materialization] result")
    print(f"  result: {result}")
    print(f"  checked_total: {len(rel_paths)}")
    print(f"  missing_total: {len(missing)}")
    print(f"  dataless_total: {len(dataless)}")
    print(f"  reasons: {', '.join(reasons) if reasons else 'none'}")

    return 0 if result != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
