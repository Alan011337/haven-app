#!/usr/bin/env python3
"""Fail-closed contract check for frontend API transport bridge."""

from __future__ import annotations

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_API_PATH = REPO_ROOT / "frontend" / "src" / "lib" / "api.ts"
FRONTEND_SRC_ROOT = REPO_ROOT / "frontend" / "src"
API_CLIENT_PATH = REPO_ROOT / "frontend" / "src" / "services" / "api-client.ts"


def main() -> int:
    if not FRONTEND_API_PATH.exists():
        print("[frontend-api-transport-contract] fail: missing frontend/src/lib/api.ts")
        return 1

    text = FRONTEND_API_PATH.read_text(encoding="utf-8")
    required_markers = [
        "isApiEnvelopePayload",
        "response.data = payload.data",
        "Idempotency-Key",
        "IDEMPOTENCY_EXEMPT_PATHS",
        "shouldAttachIdempotencyKey",
        "resolveStableIdempotencyKey",
        "_buildIdempotencyFingerprint",
        "idempotencyKeyCache",
    ]
    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        print("[frontend-api-transport-contract] fail: marker missing")
        for marker in missing:
            print(f"  - {marker}")
        return 1

    violating_files: list[Path] = []
    for path in FRONTEND_SRC_ROOT.rglob("*.ts*"):
        if not path.is_file():
            continue
        if path.resolve() == FRONTEND_API_PATH.resolve():
            continue
        file_text = path.read_text(encoding="utf-8")
        if re.search(r"^\s*import\s+axios\b", file_text, flags=re.MULTILINE):
            violating_files.append(path)
            continue
        if re.search(r"\baxios\.(create|get|post|put|patch|delete|request)\b", file_text):
            violating_files.append(path)

    if violating_files:
        print("[frontend-api-transport-contract] fail: axios import outside frontend/src/lib/api.ts")
        for path in sorted(violating_files):
            print(f"  - {path.relative_to(REPO_ROOT)}")
        return 1

    if not API_CLIENT_PATH.exists():
        print("[frontend-api-transport-contract] fail: missing frontend/src/services/api-client.ts")
        return 1

    api_client_text = API_CLIENT_PATH.read_text(encoding="utf-8")
    if "from '@/lib/api'" in api_client_text:
        print("[frontend-api-transport-contract] fail: api-client.ts must use api-transport wrappers")
        return 1
    if re.search(r"\bapi\.(get|post|put|patch|delete)\b", api_client_text):
        print("[frontend-api-transport-contract] fail: api-client.ts has direct api.* calls")
        return 1

    print("[frontend-api-transport-contract] ok: frontend transport contract markers present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
