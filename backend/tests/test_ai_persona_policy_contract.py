import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.check_ai_persona_policy_contract import (  # noqa: E402
    POLICY_PATH,
    collect_ai_persona_policy_contract_violations,
)


class AIPersonaPolicyContractTests(unittest.TestCase):
    def test_policy_contract_passes_with_repository_payload(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        violations = collect_ai_persona_policy_contract_violations(payload=payload)
        self.assertEqual(violations, [])

    def test_policy_contract_rejects_missing_immutable_policy_marker(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["immutable_policies"] = ["AI-POL-01", "AI-POL-02"]
        violations = collect_ai_persona_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("missing_immutable_policy_marker", reasons)

    def test_policy_contract_rejects_invalid_dynamic_context_feature_flag(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["dynamic_context_injection"]["feature_flag"] = "AI_DYNAMIC_CONTEXT"
        violations = collect_ai_persona_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("invalid_feature_flag", reasons)

    def test_policy_contract_rejects_missing_analysis_service_integration(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["references"]["analysis_service"] = "backend/app/core/prompts.py"
        violations = collect_ai_persona_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("missing_analysis_service_integration", reasons)

    def test_policy_contract_rejects_missing_runtime_guardrail_marker(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["runtime_output_guardrail"]["strategy"] = [
            "non_impersonation_runtime_assertion",
            "partner_identity_claim_rewrite",
        ]
        violations = collect_ai_persona_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("missing_runtime_guardrail_marker", reasons)

    def test_policy_contract_rejects_invalid_runtime_guardrail_feature_flag(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["runtime_output_guardrail"]["feature_flag"] = "AI_PERSONA_GUARDRAIL"
        violations = collect_ai_persona_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("invalid_runtime_guardrail_feature_flag", reasons)


if __name__ == "__main__":
    unittest.main()
