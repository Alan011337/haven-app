import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.check_ai_cost_quality_policy_contract import (  # noqa: E402
    POLICY_PATH,
    collect_ai_cost_quality_policy_contract_violations,
)


class AICostQualityPolicyContractTests(unittest.TestCase):
    def test_policy_contract_passes_with_repository_payload(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        violations = collect_ai_cost_quality_policy_contract_violations(payload=payload)
        self.assertEqual(violations, [])

    def test_policy_contract_rejects_invalid_schema_compliance_min(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["thresholds"]["schema_compliance_min"] = 120
        violations = collect_ai_cost_quality_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("invalid_schema_compliance_min", reasons)

    def test_policy_contract_rejects_invalid_token_budget(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["thresholds"]["token_budget_daily"] = 0
        violations = collect_ai_cost_quality_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("invalid_token_budget_daily", reasons)

    def test_policy_contract_rejects_missing_snapshot_script_integration(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["references"]["snapshot_script"] = "backend/app/core/prompts.py"
        violations = collect_ai_cost_quality_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("missing_snapshot_script_marker", reasons)

    def test_policy_contract_rejects_invalid_drift_critical_multiplier(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["drift_detection"]["critical_multiplier"] = 1.0
        violations = collect_ai_cost_quality_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("invalid_drift_critical_multiplier", reasons)

    def test_policy_contract_rejects_invalid_request_class_gate_mode(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["budget_guardrails"]["request_class_gate_mode"] = "random"
        violations = collect_ai_cost_quality_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("invalid_request_class_gate_mode", reasons)


if __name__ == "__main__":
    unittest.main()
