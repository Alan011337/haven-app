#!/usr/bin/env python3
"""Fail-closed contract check for idempotency normalization consistency."""

from __future__ import annotations

from pathlib import Path


def main() -> int:
    backend_root = Path(__file__).resolve().parents[1]
    offline_file = backend_root / "app" / "services" / "offline_idempotency.py"
    source = offline_file.read_text(encoding="utf-8")
    if "_normalize_http_idempotency_key" not in source:
        raise SystemExit(
            "[idempotency-normalization-contract] fail: offline_idempotency must reuse api_idempotency_store normalization helper."
        )
    if "return _normalize_http_idempotency_key(raw)" not in source:
        raise SystemExit(
            "[idempotency-normalization-contract] fail: normalize_idempotency_key must delegate to shared helper."
        )
    print("[idempotency-normalization-contract] result: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

