import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_quick_backend_contract_summary.py"
_SPEC = importlib.util.spec_from_file_location(
    "check_quick_backend_contract_summary", SCRIPT_PATH
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def _valid_payload() -> dict:
    return {
        "schema_version": "v1",
        "result": "pass",
        "exit_code": 0,
        "test_count": 35,
        "duration_seconds": 2,
        "log_path": "/tmp/release-gate-local-quick-backend-tests.log",
    }


class QuickBackendContractSummaryGateTests(unittest.TestCase):
    def test_validate_summary_payload_accepts_valid_payload(self) -> None:
        payload = _valid_payload()
        _MODULE.validate_summary_payload(payload, required_schema_version="v1")

    def test_validate_summary_payload_rejects_schema_mismatch(self) -> None:
        payload = _valid_payload()
        payload["schema_version"] = "v2"
        with self.assertRaises(RuntimeError):
            _MODULE.validate_summary_payload(payload, required_schema_version="v1")

    def test_validate_summary_payload_rejects_missing_key(self) -> None:
        payload = _valid_payload()
        payload.pop("duration_seconds")
        with self.assertRaises(RuntimeError):
            _MODULE.validate_summary_payload(payload, required_schema_version="v1")

    def test_validate_summary_payload_rejects_invalid_result_exit_code_pair(self) -> None:
        payload = _valid_payload()
        payload["result"] = "fail"
        payload["exit_code"] = 0
        with self.assertRaises(RuntimeError):
            _MODULE.validate_summary_payload(payload, required_schema_version="v1")

    def test_main_passes_with_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "summary.json"
            summary_path.write_text(json.dumps(_valid_payload()), encoding="utf-8")
            exit_code = _MODULE.main(
                [
                    "--summary-file",
                    str(summary_path),
                    "--required-schema-version",
                    "v1",
                ]
            )
        self.assertEqual(exit_code, 0)

    def test_main_fails_with_invalid_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "summary.json"
            payload = _valid_payload()
            payload["result"] = "degraded"
            summary_path.write_text(json.dumps(payload), encoding="utf-8")
            exit_code = _MODULE.main(
                [
                    "--summary-file",
                    str(summary_path),
                    "--required-schema-version",
                    "v1",
                ]
            )
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
