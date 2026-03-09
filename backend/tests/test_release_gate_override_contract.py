import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_release_gate_override_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_release_gate_override_contract", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class ReleaseGateOverrideContractTests(unittest.TestCase):
    def _run_main(self, env: dict[str, str], argv: list[str] | None = None) -> int:
        with patch.dict("os.environ", env, clear=True):
            if argv is None:
                return _MODULE.main([])
            return _MODULE.main(argv)

    def test_fail_closed_mode_passes_without_relaxations(self) -> None:
        exit_code = self._run_main({})
        self.assertEqual(exit_code, 0)

    def test_relaxation_requires_hotfix_override(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_ALLOW_MISSING_SLO_URL": "1",
                "RELEASE_GATE_OVERRIDE_REASON": "incident-123",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_relaxation_requires_reason(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE": "true",
                "RELEASE_GATE_HOTFIX_OVERRIDE": "true",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_relaxation_passes_with_hotfix_override_and_reason(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_ALLOW_MISSING_LAUNCH_SIGNOFF": "true",
                "RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE": "1",
                "RELEASE_GATE_HOTFIX_OVERRIDE": "1",
                "RELEASE_GATE_OVERRIDE_REASON": "sev2-prod-outage",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_relaxation_rejects_non_ticket_like_reason(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_ALLOW_MISSING_SLO_URL": "1",
                "RELEASE_GATE_HOTFIX_OVERRIDE": "1",
                "RELEASE_GATE_OVERRIDE_REASON": "this is free text not ticket id",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_relaxation_accepts_custom_reason_pattern(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_ALLOW_MISSING_SLO_URL": "1",
                "RELEASE_GATE_HOTFIX_OVERRIDE": "1",
                "RELEASE_GATE_OVERRIDE_REASON_PATTERN": r"^INC-[0-9]{4}$",
                "RELEASE_GATE_OVERRIDE_REASON": "INC-2026",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_invalid_bool_value_fails_contract(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_ALLOW_MISSING_SLO_URL": "maybe",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_invalid_reason_pattern_fails_contract(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_OVERRIDE_REASON_PATTERN": "[invalid",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_summary_contains_override_reason_value_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary_path = str(Path(tmp_dir) / "override-summary.json")

            exit_code = self._run_main(
                {
                    "RELEASE_GATE_ALLOW_MISSING_SLO_URL": "1",
                    "RELEASE_GATE_HOTFIX_OVERRIDE": "1",
                    "RELEASE_GATE_OVERRIDE_REASON": "INC-2026-021",
                    "RELEASE_GATE_OVERRIDE_REASON_PATTERN": r"^INC-[0-9-]{8,20}$",
                },
                ["--summary-path", summary_path],
            )
            self.assertEqual(exit_code, 0)

            payload = json.loads(Path(summary_path).read_text(encoding="utf-8"))
            self.assertEqual(payload.get("override_reason"), "INC-2026-021")
            self.assertTrue(payload.get("override_reason_present"))


if __name__ == "__main__":
    unittest.main()
