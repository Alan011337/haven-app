import importlib.util
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_event_tracking_privacy_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_event_tracking_privacy_contract", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class EventTrackingPrivacyContractTests(unittest.TestCase):
    def test_event_tracking_privacy_contract_passes_repository_state(self) -> None:
        violations = _MODULE.collect_event_tracking_privacy_violations()
        self.assertEqual(violations, [])

    def test_event_tracking_privacy_contract_detects_missing_fragment(self) -> None:
        backend_text = _MODULE.BACKEND_POSTHOG_PATH.read_text(encoding="utf-8")
        frontend_text = _MODULE.FRONTEND_POSTHOG_PATH.read_text(encoding="utf-8")
        doc_text = _MODULE.ALPHA_GATE_DOC_PATH.read_text(encoding="utf-8")
        self.assertIn("email", backend_text.lower())
        self.assertIn("email", frontend_text.lower())
        self.assertIn("distinct id", doc_text.lower())


if __name__ == "__main__":
    unittest.main()
