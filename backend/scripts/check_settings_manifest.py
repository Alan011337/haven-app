#!/usr/bin/env python3
"""Validate grouped settings manifest stays aligned with Settings model."""

from __future__ import annotations

import json

from app.core.config import settings
from app.core.settings_manifest import validate_manifest_against_settings


def main() -> int:
    report = validate_manifest_against_settings(settings)
    missing_domains = {domain: missing for domain, missing in report.items() if missing}
    if missing_domains:
        print(
            json.dumps(
                {
                    "result": "fail",
                    "missing": missing_domains,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "result": "ok",
                "domains": sorted(report.keys()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
