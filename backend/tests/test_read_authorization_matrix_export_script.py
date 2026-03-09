from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "export_read_authorization_matrix.py"
_SPEC = importlib.util.spec_from_file_location("export_read_authorization_matrix", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load script from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class ReadAuthorizationMatrixExportScriptTests(unittest.TestCase):
    def test_generated_payload_covers_critical_read_keys(self) -> None:
        matrix_payload = json.loads((_MODULE.DEFAULT_MATRIX_PATH).read_text(encoding="utf-8"))
        inventory_payload = json.loads((_MODULE.DEFAULT_INVENTORY_PATH).read_text(encoding="utf-8"))
        payload = _MODULE.build_generated_read_matrix_payload(
            matrix_payload=matrix_payload,
            inventory_payload=inventory_payload,
        )
        entries = payload.get("entries", [])
        keys = {(entry["method"], entry["path"]) for entry in entries}
        self.assertEqual(keys, set(_MODULE.CRITICAL_READ_KEYS))

    def test_check_current_passes_for_current_repository_state(self) -> None:
        matrix_payload = json.loads((_MODULE.DEFAULT_MATRIX_PATH).read_text(encoding="utf-8"))
        inventory_payload = json.loads((_MODULE.DEFAULT_INVENTORY_PATH).read_text(encoding="utf-8"))
        errors = _MODULE.check_read_matrix_drift(
            matrix_payload=matrix_payload,
            inventory_payload=inventory_payload,
        )
        self.assertEqual(errors, [])

    def test_script_writes_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "read-matrix.generated.json"
            code = _MODULE.main(
                [
                    "--matrix",
                    str(_MODULE.DEFAULT_MATRIX_PATH),
                    "--inventory",
                    str(_MODULE.DEFAULT_INVENTORY_PATH),
                    "--output",
                    str(output_path),
                    "--write-draft",
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue(output_path.exists())
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("artifact_kind"), "read-authorization-matrix")


if __name__ == "__main__":
    unittest.main()
