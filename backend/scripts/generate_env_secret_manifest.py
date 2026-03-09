#!/usr/bin/env python3
"""Regenerate env/secrets manifest from backend/frontend env checks."""

from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_RELATIVE_PATH = "docs/ops/env-secrets-manifest.json"
BACKEND_ENV_CHECK_RELATIVE_PATH = "backend/scripts/check_env.py"
FRONTEND_ENV_CHECK_RELATIVE_PATH = "frontend/scripts/check-env.mjs"
MANIFEST_PATH = REPO_ROOT / MANIFEST_RELATIVE_PATH
BACKEND_ENV_CHECK_PATH = REPO_ROOT / BACKEND_ENV_CHECK_RELATIVE_PATH
FRONTEND_ENV_CHECK_PATH = REPO_ROOT / FRONTEND_ENV_CHECK_RELATIVE_PATH


def _extract_backend_required_keys(text: str) -> list[str]:
    match = re.search(r"REQUIRED_KEYS\s*=\s*\((.*?)\)\n\n", text, flags=re.S)
    if not match:
        return []
    block = match.group(1)
    return sorted(set(re.findall(r'"([A-Z0-9_]+)"', block)))


def _extract_backend_optional_keys(text: str) -> list[str]:
    match = re.search(r"OPTIONAL_KEYS\s*=\s*\((.*?)\)\n\n", text, flags=re.S)
    if not match:
        return []
    block = match.group(1)
    return sorted(set(re.findall(r'"([A-Z0-9_]+)"', block)))


def _extract_frontend_required_keys(text: str) -> list[str]:
    match = re.search(r"const required\s*=\s*\[(.*?)\];", text, flags=re.S)
    if not match:
        return []
    block = match.group(1)
    return sorted(set(re.findall(r"'([A-Z0-9_]+)'", block)))


def main() -> int:
    existing: dict[str, object] = {}
    if MANIFEST_PATH.exists():
        existing = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    backend_env_check_text = BACKEND_ENV_CHECK_PATH.read_text(encoding="utf-8")
    backend_required = _extract_backend_required_keys(backend_env_check_text)
    backend_optional = _extract_backend_optional_keys(backend_env_check_text)
    frontend_required = _extract_frontend_required_keys(
        FRONTEND_ENV_CHECK_PATH.read_text(encoding="utf-8")
    )

    payload = {
        "schema_version": "v1",
        "backend_required": backend_required,
        "backend_optional_documented": backend_optional,
        "frontend_required": frontend_required,
        "runtime_switches": existing.get(
            "runtime_switches",
            [
                "WEBSOCKET_ENABLED",
                "WEBPUSH_ENABLED",
                "EMAIL_NOTIFICATIONS_ENABLED",
                "TIMELINE_CURSOR_ENABLED",
                "SAFETY_MODE_ENABLED",
            ],
        ),
        "sensitive_backend_optional": existing.get(
            "sensitive_backend_optional",
            [
                "AI_ROUTER_REDIS_URL",
                "RESEND_API_KEY",
                "BILLING_STRIPE_SECRET_KEY",
                "BILLING_STRIPE_WEBHOOK_SECRET",
                "POSTHOG_API_KEY",
                "VAPID_PRIVATE_KEY",
            ],
        ),
    }
    MANIFEST_PATH.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"[generate-env-secret-manifest] wrote: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
