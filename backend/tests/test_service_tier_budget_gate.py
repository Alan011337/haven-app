import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_service_tier_budget_gate.py"
_SPEC = importlib.util.spec_from_file_location("check_service_tier_budget_gate", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def _policy_payload() -> dict:
    return {
        "schema_version": "1.0.0",
        "default_target_tier": "tier_0",
        "tiers": {
            "tier_0": {
                "display_name": "Core CUJ",
                "error_budget_freeze_enforced": True,
                "allowed_release_intents_when_frozen": ["bugfix", "security", "hotfix"],
            },
            "tier_1": {
                "display_name": "Non-core",
                "error_budget_freeze_enforced": False,
                "allowed_release_intents_when_frozen": ["feature", "bugfix", "security", "hotfix"],
            },
        },
    }


class ServiceTierBudgetGateTests(unittest.TestCase):
    def test_evaluate_fails_tier0_feature_when_freeze_active(self) -> None:
        passed, reasons, meta = _MODULE.evaluate_service_tier_gate(
            policy=_policy_payload(),
            status_payload={"release_freeze": True, "checked_at": "2026-02-22T00:00:00Z"},
            target_tier="tier_0",
            release_intent="feature",
            hotfix_override=False,
        )
        self.assertFalse(passed)
        self.assertIn("tier_error_budget_freeze_active", reasons)
        self.assertTrue(meta["tier_error_budget_freeze_enforced"])

    def test_evaluate_passes_tier1_feature_when_freeze_active(self) -> None:
        passed, reasons, meta = _MODULE.evaluate_service_tier_gate(
            policy=_policy_payload(),
            status_payload={"release_freeze": True, "checked_at": "2026-02-22T00:00:00Z"},
            target_tier="tier_1",
            release_intent="feature",
            hotfix_override=False,
        )
        self.assertTrue(passed)
        self.assertIn("release_intent_allowed_during_freeze", reasons)
        self.assertFalse(meta["tier_error_budget_freeze_enforced"])

    def test_main_accepts_missing_status_with_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_path = Path(tmp_dir) / "policy.json"
            policy_path.write_text(json.dumps(_policy_payload()), encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                exit_code = _MODULE.main(
                    [
                        "--policy-file",
                        str(policy_path),
                        "--status-file",
                        str(Path(tmp_dir) / "missing-status.json"),
                        "--allow-missing-status",
                    ]
                )
        self.assertEqual(exit_code, 0)

    def test_main_fails_invalid_target_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_path = Path(tmp_dir) / "policy.json"
            status_path = Path(tmp_dir) / "status.json"
            policy_path.write_text(json.dumps(_policy_payload()), encoding="utf-8")
            status_path.write_text(json.dumps({"release_freeze": False}), encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                exit_code = _MODULE.main(
                    [
                        "--policy-file",
                        str(policy_path),
                        "--status-file",
                        str(status_path),
                        "--target-tier",
                        "tier_x",
                    ]
                )
        self.assertEqual(exit_code, 1)

    def test_main_passes_tier0_hotfix_when_freeze_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_path = Path(tmp_dir) / "policy.json"
            status_path = Path(tmp_dir) / "status.json"
            policy_path.write_text(json.dumps(_policy_payload()), encoding="utf-8")
            status_path.write_text(
                json.dumps({"release_freeze": True, "checked_at": "2026-02-22T00:00:00Z"}),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                exit_code = _MODULE.main(
                    [
                        "--policy-file",
                        str(policy_path),
                        "--status-file",
                        str(status_path),
                        "--target-tier",
                        "tier_0",
                        "--release-intent",
                        "hotfix",
                    ]
                )
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
