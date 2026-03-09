import importlib.util
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_deploy_source_of_truth.py"
SPEC = importlib.util.spec_from_file_location("check_deploy_source_of_truth", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)  # type: ignore[arg-type]


class DeploySourceOfTruthContractTests(unittest.TestCase):
    def test_deploy_source_of_truth_contract_passes(self) -> None:
        self.assertEqual(MODULE.collect_violations(), [])

    def test_backend_fly_declares_ai_router_shared_state_backend(self) -> None:
        text = MODULE.BACKEND_FLY.read_text(encoding="utf-8")
        self.assertIn('AI_ROUTER_SHARED_STATE_BACKEND = "redis"', text)

    def test_render_archived_blueprint_keeps_ai_router_shared_state_secret_marker(self) -> None:
        text = MODULE.RENDER_BLUEPRINT.read_text(encoding="utf-8")
        self.assertIn("- key: AI_ROUTER_SHARED_STATE_BACKEND", text)
        self.assertIn("- key: AI_ROUTER_REDIS_URL", text)


if __name__ == "__main__":
    unittest.main()
