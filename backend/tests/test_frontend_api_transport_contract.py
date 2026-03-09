from __future__ import annotations

import importlib.util
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_frontend_api_transport_contract.py"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

_SPEC = importlib.util.spec_from_file_location("check_frontend_api_transport_contract", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class FrontendApiTransportContractTests(unittest.TestCase):
    def test_main_passes_with_current_contract(self) -> None:
        self.assertEqual(_MODULE.main(), 0)

    def test_main_fails_when_required_marker_missing(self) -> None:
        original = _MODULE.FRONTEND_API_PATH.read_text(encoding="utf-8")
        mutated = original.replace("Idempotency-Key", "IdempotencyKey")
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate = Path(tmp_dir) / "api.ts"
            candidate.write_text(mutated, encoding="utf-8")
            with patch.object(_MODULE, "FRONTEND_API_PATH", candidate):
                self.assertEqual(_MODULE.main(), 1)

    def test_main_fails_when_axios_import_exists_outside_transport(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            src_root = root / "src"
            api_path = src_root / "lib" / "api.ts"
            api_path.parent.mkdir(parents=True, exist_ok=True)
            api_path.write_text(_MODULE.FRONTEND_API_PATH.read_text(encoding="utf-8"), encoding="utf-8")

            violating = src_root / "services" / "foo.ts"
            violating.parent.mkdir(parents=True, exist_ok=True)
            violating.write_text('import axios from "axios";\nexport const x = 1;\n', encoding="utf-8")

            with (
                patch.object(_MODULE, "FRONTEND_API_PATH", api_path),
                patch.object(_MODULE, "FRONTEND_SRC_ROOT", src_root),
                patch.object(_MODULE, "API_CLIENT_PATH", src_root / "services" / "api-client.ts"),
                patch.object(_MODULE, "REPO_ROOT", root),
            ):
                self.assertEqual(_MODULE.main(), 1)

    def test_main_fails_when_api_client_imports_lib_api_directly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            src_root = root / "src"
            api_path = src_root / "lib" / "api.ts"
            api_path.parent.mkdir(parents=True, exist_ok=True)
            api_path.write_text(_MODULE.FRONTEND_API_PATH.read_text(encoding="utf-8"), encoding="utf-8")

            api_client = src_root / "services" / "api-client.ts"
            api_client.parent.mkdir(parents=True, exist_ok=True)
            api_client.write_text("import api from '@/lib/api';\nexport const x = 1;\n", encoding="utf-8")

            with (
                patch.object(_MODULE, "FRONTEND_API_PATH", api_path),
                patch.object(_MODULE, "FRONTEND_SRC_ROOT", src_root),
                patch.object(_MODULE, "API_CLIENT_PATH", api_client),
                patch.object(_MODULE, "REPO_ROOT", root),
            ):
                self.assertEqual(_MODULE.main(), 1)


if __name__ == "__main__":
    unittest.main()
