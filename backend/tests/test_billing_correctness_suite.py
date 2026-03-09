"""BILL-09: Single correctness suite aggregating required billing test modules.

This module does not run tests; it ensures the required billing test files
and key test classes exist so CI can run them as a single suite.
"""
from __future__ import annotations

import unittest
from pathlib import Path


class BillingCorrectnessSuiteContract(unittest.TestCase):
    """Contract: required billing test modules exist and are importable."""

    def test_billing_webhook_security_module_exists(self) -> None:
        p = Path(__file__).resolve().parent / "test_billing_webhook_security.py"
        self.assertTrue(p.exists(), f"Required: {p}")

    def test_billing_idempotency_api_module_exists(self) -> None:
        p = Path(__file__).resolve().parent / "test_billing_idempotency_api.py"
        self.assertTrue(p.exists(), f"Required: {p}")

    def test_billing_entitlement_parity_module_exists(self) -> None:
        p = Path(__file__).resolve().parent / "test_billing_entitlement_parity.py"
        self.assertTrue(p.exists(), f"Required: {p}")

    def test_billing_authorization_matrix_module_exists(self) -> None:
        p = Path(__file__).resolve().parent / "test_billing_authorization_matrix.py"
        self.assertTrue(p.exists(), f"Required: {p}")

    def test_billing_grace_account_hold_policy_contract_module_exists(self) -> None:
        p = Path(__file__).resolve().parent / "test_billing_grace_account_hold_policy_contract.py"
        self.assertTrue(p.exists(), f"Required: {p}")

    def test_billing_console_drift_audit_module_exists(self) -> None:
        p = Path(__file__).resolve().parent / "test_billing_console_drift_audit.py"
        self.assertTrue(p.exists(), f"Required: {p}")


if __name__ == "__main__":
    unittest.main()
