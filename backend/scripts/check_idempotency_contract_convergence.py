#!/usr/bin/env python3
"""Check cross-stack idempotency contract convergence markers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-path", default="")
    return parser


def _write(path: str, payload: dict[str, Any]) -> None:
    if not path:
        return
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def _contains_all(path: Path, markers: list[str]) -> list[str]:
    if not path.exists():
        return [f"missing_file:{path}"]
    content = path.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in content]
    return [f"missing_marker:{path}:{marker}" for marker in missing]


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    violations: list[str] = []
    violations.extend(
        _contains_all(
            REPO_ROOT / "frontend/src/lib/api.ts",
            [
                "IDEMPOTENCY_EXEMPT_PATHS",
                "shouldAttachIdempotencyKey",
                "Idempotency-Key",
            ],
        )
    )
    violations.extend(
        _contains_all(
            REPO_ROOT / "frontend/src/services/api-client.ts",
            [
                "idempotencyKey",
                "Idempotency-Key",
            ],
        )
    )
    violations.extend(
        _contains_all(
            REPO_ROOT / "backend/scripts/check_write_idempotency_coverage.py",
            [
                "mutating_api_total",
                "exempt_total",
            ],
        )
    )
    violations.extend(
        _contains_all(
            REPO_ROOT / "backend/scripts/check_idempotency_normalization_contract.py",
            [
                "normalize_idempotency_key",
                "api_idempotency_store",
            ],
        )
    )

    result = "pass" if not violations else "fail"
    payload = {
        "result": result,
        "reasons": ["idempotency_contract_diverged"] if violations else [],
        "meta": {"violation_total": len(violations)},
        "violations": violations,
    }
    _write(args.summary_path, payload)
    print("[idempotency-contract-convergence] result")
    print(f"  result: {result}")
    print(f"  violation_total: {len(violations)}")
    if violations:
        for violation in violations:
            print(f"  - {violation}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
