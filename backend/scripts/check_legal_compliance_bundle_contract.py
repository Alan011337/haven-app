#!/usr/bin/env python3
"""Policy-as-code gate for legal compliance bundle (P0-G)."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

POLICY_PATH = REPO_ROOT / "docs" / "security" / "legal-compliance-bundle.json"

SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "legal-compliance-bundle"


@dataclass(frozen=True)
class LegalComplianceViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _validate_versioned_legal_markdown(path: Path) -> list[str]:
    text = _read_text(path)
    issues: list[str] = []
    if not re.search(r"\*\*版本\*\*\s*[:：]\s*\d+\.\d+\.\d+", text):
        issues.append(f"{path} missing semantic version marker")
    if not re.search(r"\*\*最後更新\*\*\s*[:：]\s*\d{4}-\d{2}-\d{2}", text):
        issues.append(f"{path} missing last-updated marker")
    return issues


def collect_legal_compliance_bundle_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[LegalComplianceViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[LegalComplianceViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            LegalComplianceViolation("invalid_schema_version", f"schema_version must be `{SCHEMA_VERSION}`.")
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            LegalComplianceViolation("invalid_artifact_kind", f"artifact_kind must be `{ARTIFACT_KIND}`.")
        )

    docs = policy.get("documents")
    if not isinstance(docs, dict):
        violations.append(LegalComplianceViolation("invalid_documents", "documents must be object."))
    else:
        for key in ("privacy_policy", "terms_of_service", "ai_policy"):
            entry = docs.get(key)
            if not isinstance(entry, dict):
                violations.append(LegalComplianceViolation("missing_document", f"documents.{key} must be object."))
                continue
            doc_path = entry.get("path")
            if not isinstance(doc_path, str) or not doc_path.strip():
                violations.append(LegalComplianceViolation("invalid_document_path", f"documents.{key}.path required."))
                continue
            abs_path = REPO_ROOT / doc_path
            if not abs_path.exists():
                violations.append(
                    LegalComplianceViolation("missing_document_file", f"documents.{key}.path not found: {doc_path}")
                )
                continue
            if key in {"privacy_policy", "terms_of_service"}:
                for issue in _validate_versioned_legal_markdown(abs_path):
                    violations.append(LegalComplianceViolation("invalid_legal_doc_format", issue))

        ai_path_value = docs.get("ai_policy", {}).get("path")
        if isinstance(ai_path_value, str):
            ai_path = REPO_ROOT / ai_path_value
            if ai_path.exists():
                ai_text = _read_text(ai_path)
                for marker in ("AI-POL-01", "AI-POL-02", "AI-POL-03"):
                    if marker not in ai_text:
                        violations.append(
                            LegalComplianceViolation("missing_ai_policy_marker", f"AI policy missing marker `{marker}`.")
                        )

        tos_path_value = docs.get("terms_of_service", {}).get("path")
        if isinstance(tos_path_value, str):
            tos_path = REPO_ROOT / tos_path_value
            if tos_path.exists() and "18 歲" not in _read_text(tos_path):
                violations.append(
                    LegalComplianceViolation(
                        "missing_age_clause",
                        "Terms of Service must explicitly contain `18 歲` age restriction.",
                    )
                )

    age_gating = policy.get("age_gating")
    if not isinstance(age_gating, dict):
        violations.append(LegalComplianceViolation("invalid_age_gating", "age_gating must be object."))
    else:
        minimum_age = age_gating.get("minimum_age")
        if minimum_age != 18:
            violations.append(LegalComplianceViolation("invalid_minimum_age", "age_gating.minimum_age must be 18."))
        register_page_path = age_gating.get("register_page_path")
        if not isinstance(register_page_path, str) or not register_page_path.strip():
            violations.append(
                LegalComplianceViolation("invalid_register_page_path", "age_gating.register_page_path required.")
            )
        else:
            register_abs = REPO_ROOT / register_page_path
            if not register_abs.exists():
                violations.append(
                    LegalComplianceViolation(
                        "missing_register_page",
                        f"age_gating.register_page_path not found: {register_page_path}",
                    )
                )
            else:
                register_text = _read_text(register_abs)
                if "18 歲" not in register_text:
                    violations.append(
                        LegalComplianceViolation("missing_register_age_text", "register page must include `18 歲` text.")
                    )
                required_links = age_gating.get("required_links")
                if not isinstance(required_links, list) or not required_links:
                    violations.append(
                        LegalComplianceViolation("invalid_required_links", "age_gating.required_links must be list.")
                    )
                else:
                    for link in required_links:
                        if not isinstance(link, str) or link not in register_text:
                            violations.append(
                                LegalComplianceViolation(
                                    "missing_register_required_link",
                                    f"register page missing required link `{link}`.",
                                )
                            )

    consent_receipt = policy.get("consent_receipt")
    if not isinstance(consent_receipt, dict):
        violations.append(LegalComplianceViolation("invalid_consent_receipt", "consent_receipt must be object."))
    else:
        if consent_receipt.get("event_action") != "USER_CONSENT_ACK":
            violations.append(
                LegalComplianceViolation(
                    "invalid_consent_event_action",
                    "consent_receipt.event_action must be USER_CONSENT_ACK.",
                )
            )
        api_test_path = consent_receipt.get("api_test_path")
        if not isinstance(api_test_path, str) or not api_test_path.strip():
            violations.append(
                LegalComplianceViolation(
                    "invalid_consent_test_path",
                    "consent_receipt.api_test_path must be non-empty path.",
                )
            )
        elif not (REPO_ROOT / api_test_path).exists():
            violations.append(
                LegalComplianceViolation(
                    "missing_consent_test_file",
                    f"consent_receipt.api_test_path not found: {api_test_path}",
                )
            )

    refs = policy.get("references")
    if not isinstance(refs, dict) or not refs:
        violations.append(LegalComplianceViolation("invalid_references", "references must be non-empty object."))
    else:
        for key, rel_path in refs.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(
                    LegalComplianceViolation("invalid_reference_path", f"references.{key} must be path.")
                )
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    LegalComplianceViolation("missing_reference_file", f"references.{key} not found: {rel_path}")
                )

    return violations


def run_policy_check() -> int:
    violations = collect_legal_compliance_bundle_contract_violations()
    if not violations:
        print("[legal-compliance-bundle-contract] ok: legal compliance bundle contract satisfied")
        return 0
    print("[legal-compliance-bundle-contract] failed:", file=sys.stderr)
    for v in violations:
        print(f"  - reason={v.reason} details={v.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
