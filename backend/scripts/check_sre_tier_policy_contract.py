#!/usr/bin/env python3
"""SRE-TIER-01: Validate service-tier policy JSON for release checks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
POLICY_PATHS = [
    REPO_ROOT / "docs" / "sre" / "service-tier-policy.json",
    REPO_ROOT / "docs" / "sre" / "service-tiering.json",
]


def main() -> int:
    path = None
    for p in POLICY_PATHS:
        if p.exists():
            path = p
            break
    if not path:
        print("SRE-TIER-01: No tier policy file found", file=sys.stderr)
        return 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"SRE-TIER-01: Invalid or unreadable policy {path}: {e}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("SRE-TIER-01: Policy root must be an object", file=sys.stderr)
        return 1
    tiers = data.get("tiers")
    if not isinstance(tiers, dict) or "tier_0" not in tiers or "tier_1" not in tiers:
        print("SRE-TIER-01: Policy must have tiers.tier_0 and tiers.tier_1", file=sys.stderr)
        return 1
    print(f"SRE-TIER-01: Tier policy valid: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
