import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.check_ai_router_policy_contract import (  # noqa: E402
    POLICY_PATH,
    collect_ai_router_policy_contract_violations,
)


class AIRouterPolicyContractTests(unittest.TestCase):
    def test_policy_contract_passes_with_repository_payload(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        violations = collect_ai_router_policy_contract_violations(payload=payload)
        self.assertEqual(violations, [])

    def test_policy_contract_rejects_missing_provider(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["supported_providers"] = ["openai"]
        violations = collect_ai_router_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("missing_supported_provider", reasons)

    def test_policy_contract_rejects_invalid_default_primary_provider(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["routing"]["default_primary_provider"] = "gemini"
        violations = collect_ai_router_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("invalid_default_primary_provider", reasons)

    def test_policy_contract_rejects_invalid_analysis_task(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["routing"]["analysis_task"] = "unknown_task"
        violations = collect_ai_router_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("invalid_analysis_task", reasons)

    def test_policy_contract_rejects_missing_task_policy_entry(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["routing"]["task_policy"].pop("l2_deep_reasoning", None)
        violations = collect_ai_router_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("missing_task_policy_entry", reasons)

    def test_policy_contract_rejects_missing_analysis_router_integration(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["references"]["analysis_service"] = "backend/app/core/prompts.py"
        violations = collect_ai_router_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("missing_analysis_router_integration", reasons)

    def test_policy_contract_rejects_invalid_runtime_idempotency_action(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["runtime_policy"]["idempotency"]["mismatch_action"] = "unsupported"
        violations = collect_ai_router_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("invalid_idempotency_mismatch_action", reasons)

    def test_policy_contract_rejects_invalid_duplicate_exit_action(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["runtime_policy"]["duplicate_handling"]["exit_action"] = "wait_forever"
        violations = collect_ai_router_policy_contract_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("invalid_duplicate_exit_action", reasons)


if __name__ == "__main__":
    unittest.main()
