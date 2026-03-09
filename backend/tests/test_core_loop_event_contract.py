from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_core_loop_event_contract.py"

_SPEC = importlib.util.spec_from_file_location("check_core_loop_event_contract", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class CoreLoopEventContractTests(unittest.TestCase):
    def test_contract_passes_with_current_repo_state(self) -> None:
        self.assertEqual(_MODULE.main(), 0)

    def test_contract_fails_when_frontend_props_contract_drops_required_key(self) -> None:
        original = _MODULE.FRONTEND_CONTRACT_PATH.read_text(encoding="utf-8")
        mutated = original.replace("'content_length',\n", "")
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate = Path(tmp_dir) / "core-loop-event-contract.ts"
            candidate.write_text(mutated, encoding="utf-8")
            with patch.object(_MODULE, "FRONTEND_CONTRACT_PATH", candidate):
                self.assertEqual(_MODULE.main(), 1)

    def test_contract_fails_when_tracker_skips_sanitizer(self) -> None:
        original = _MODULE.FRONTEND_TRACKER_PATH.read_text(encoding="utf-8")
        mutated = original.replace("sanitizeCoreLoopProps", "sanitizeUnknownProps")
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate = Path(tmp_dir) / "relationship-events.ts"
            candidate.write_text(mutated, encoding="utf-8")
            with patch.object(_MODULE, "FRONTEND_TRACKER_PATH", candidate):
                self.assertEqual(_MODULE.main(), 1)


if __name__ == "__main__":
    unittest.main()
