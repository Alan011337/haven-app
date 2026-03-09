#!/usr/bin/env python3
"""Policy-as-code gate for STRIDE threat model contract."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

THREAT_MODEL_PATH = REPO_ROOT / "docs" / "security" / "threat-model-stride.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "threat-model-stride"
ALLOWED_STRIDE = {
    "spoofing",
    "tampering",
    "repudiation",
    "information_disclosure",
    "denial_of_service",
    "elevation_of_privilege",
}


@dataclass(frozen=True)
class ThreatModelViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_threat_model_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[ThreatModelViolation]:
    model = payload if payload is not None else _load_json(THREAT_MODEL_PATH)
    violations: list[ThreatModelViolation] = []

    if model.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            ThreatModelViolation(
                reason="invalid_schema_version",
                details=f"schema_version must be `{SCHEMA_VERSION}`.",
            )
        )
    if model.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            ThreatModelViolation(
                reason="invalid_artifact_kind",
                details=f"artifact_kind must be `{ARTIFACT_KIND}`.",
            )
        )

    for section in ("assets", "actors", "trust_boundaries", "threats"):
        items = model.get(section)
        if not isinstance(items, list) or not items:
            violations.append(
                ThreatModelViolation(
                    reason=f"invalid_{section}",
                    details=f"{section} must be a non-empty list.",
                )
            )
            continue
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                violations.append(
                    ThreatModelViolation(
                        reason=f"invalid_{section}_entry",
                        details=f"{section}[{idx}] must be an object.",
                    )
                )
                continue
            if not str(item.get("id", "")).strip():
                violations.append(
                    ThreatModelViolation(
                        reason=f"missing_{section}_id",
                        details=f"{section}[{idx}].id must be non-empty.",
                    )
                )
            if not str(item.get("description", "")).strip():
                violations.append(
                    ThreatModelViolation(
                        reason=f"missing_{section}_description",
                        details=f"{section}[{idx}].description must be non-empty.",
                    )
                )

    threats = model.get("threats", [])
    if isinstance(threats, list):
        for idx, item in enumerate(threats):
            if not isinstance(item, dict):
                continue
            stride = str(item.get("stride", "")).strip()
            if stride not in ALLOWED_STRIDE:
                violations.append(
                    ThreatModelViolation(
                        reason="invalid_stride_label",
                        details=f"threats[{idx}].stride `{stride}` is invalid.",
                    )
                )
            controls = item.get("controls")
            if not isinstance(controls, list) or not controls:
                violations.append(
                    ThreatModelViolation(
                        reason="missing_threat_controls",
                        details=f"threats[{idx}].controls must be non-empty list.",
                    )
                )

    refs = model.get("control_references")
    if not isinstance(refs, dict) or not refs:
        violations.append(
            ThreatModelViolation(
                reason="invalid_control_references",
                details="control_references must be a non-empty object.",
            )
        )
    else:
        for key, rel_path in refs.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(
                    ThreatModelViolation(
                        reason="invalid_reference_path",
                        details=f"control_references.{key} must be non-empty path.",
                    )
                )
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    ThreatModelViolation(
                        reason="missing_reference_file",
                        details=f"control_references.{key} file not found: {rel_path}",
                    )
                )

    return violations


def run_policy_check() -> int:
    violations = collect_threat_model_contract_violations()
    if not violations:
        print("[threat-model-contract] ok: threat model contract satisfied")
        return 0
    print("[threat-model-contract] failed:", file=sys.stderr)
    for v in violations:
        print(f"  - reason={v.reason} details={v.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
