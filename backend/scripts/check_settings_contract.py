#!/usr/bin/env python3
from __future__ import annotations

import json

from app.core.config import settings
from app.core.settings_contract import validate_settings_contract


def main() -> int:
    errors = validate_settings_contract(settings)
    summary = {
        "result": "pass" if not errors else "fail",
        "error_total": len(errors),
        "errors": errors,
    }
    print("[settings-contract] result")
    print(json.dumps(summary, ensure_ascii=True))
    if errors:
        for reason in errors:
            print(f"[settings-contract] error: {reason}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
