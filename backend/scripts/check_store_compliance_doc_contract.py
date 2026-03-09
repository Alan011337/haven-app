#!/usr/bin/env python3
"""BILL-08: Validate store compliance doc exists and references release checklist."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOC_PATH = REPO_ROOT / "docs" / "billing" / "store-compliance.md"
REQUIRED_PHRASES = ("entitlement", "parity", "test_billing_entitlement_parity")


def main() -> int:
    if not DOC_PATH.exists():
        print(f"BILL-08: Store compliance doc missing: {DOC_PATH}", file=sys.stderr)
        return 1
    text = DOC_PATH.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            print(f"BILL-08: Doc must reference '{phrase}': {DOC_PATH}", file=sys.stderr)
            return 1
    print(f"BILL-08: Store compliance doc valid: {DOC_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
