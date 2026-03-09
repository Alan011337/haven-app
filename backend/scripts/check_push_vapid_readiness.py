#!/usr/bin/env python3
"""P1-C-WEB-PUSH: Check that push/VAPID is ready for E2E (keys set; optional pywebpush import).

Exit 0 if PUSH_VAPID_PUBLIC_KEY and PUSH_VAPID_PRIVATE_KEY are set (non-empty).
Exit 1 otherwise. Use in CI to enforce push configuration or allow-missing for non-push envs.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402


def main() -> int:
    pub = (settings.PUSH_VAPID_PUBLIC_KEY or "").strip()
    priv = (settings.PUSH_VAPID_PRIVATE_KEY or "").strip()
    if pub and priv:
        print("[push-vapid-readiness] ok: VAPID keys set")
        return 0
    print("[push-vapid-readiness] not ready: PUSH_VAPID_PUBLIC_KEY and PUSH_VAPID_PRIVATE_KEY must be set")
    return 1


if __name__ == "__main__":
    sys.exit(main())
