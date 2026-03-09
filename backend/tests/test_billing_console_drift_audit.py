import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_billing_console_drift_audit.py"
SPEC = importlib.util.spec_from_file_location("run_billing_console_drift_audit", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BillingConsoleDriftAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_secret = MODULE.settings.BILLING_STRIPE_WEBHOOK_SECRET
        self._old_tolerance = MODULE.settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS
        self._old_async_mode = MODULE.settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE

    def tearDown(self) -> None:
        MODULE.settings.BILLING_STRIPE_WEBHOOK_SECRET = self._old_secret
        MODULE.settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS = self._old_tolerance
        MODULE.settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = self._old_async_mode

    def test_run_audit_writes_evidence_files(self) -> None:
        MODULE.settings.BILLING_STRIPE_WEBHOOK_SECRET = "whsec_test"
        MODULE.settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS = 300
        MODULE.settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = False

        with tempfile.TemporaryDirectory() as tmp_dir:
            payload, json_path, md_path = MODULE.run_billing_console_drift_audit(
                evidence_dir=Path(tmp_dir),
                now_utc=datetime(2026, 2, 23, 5, 0, tzinfo=UTC),
            )

            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["artifact_kind"], MODULE.ARTIFACT_KIND)
            self.assertEqual(loaded["generated_by"], MODULE.GENERATED_BY)
            self.assertEqual(loaded["contract_mode"], MODULE.CONTRACT_MODE)
            self.assertEqual(loaded["required_checks"], list(MODULE.REQUIRED_CHECKS))
            self.assertEqual(payload["checks_total"], len(MODULE.REQUIRED_CHECKS))

    def test_missing_webhook_secret_marks_check_failed(self) -> None:
        MODULE.settings.BILLING_STRIPE_WEBHOOK_SECRET = ""
        MODULE.settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS = 300
        MODULE.settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = False

        with tempfile.TemporaryDirectory() as tmp_dir:
            payload, _, _ = MODULE.run_billing_console_drift_audit(
                evidence_dir=Path(tmp_dir),
                now_utc=datetime(2026, 2, 23, 5, 0, tzinfo=UTC),
            )
        checks_by_name = {item["name"]: item for item in payload["results"]}
        self.assertFalse(checks_by_name["webhook_secret_configured"]["ok"])
        self.assertFalse(payload["all_passed"])


if __name__ == "__main__":
    unittest.main()
