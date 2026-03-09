import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_canary_guard.py"
_SPEC = importlib.util.spec_from_file_location("run_canary_guard", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

main = _MODULE.main
run_canary_guard = _MODULE.run_canary_guard


class CanaryGuardTests(unittest.TestCase):
    def test_run_canary_guard_passes_when_all_samples_pass(self) -> None:
        def fetch_sample_fn(**_kwargs):
            return True, [], {"ws": "ok", "ws_burn_rate": "ok"}

        passed, summary = run_canary_guard(
            health_url="https://example.com/health/slo",
            health_bearer_token=None,
            require_sufficient_data=False,
            duration_seconds=60,
            interval_seconds=30,
            max_failures=1,
            timeout_seconds=1,
            target_percent=1.0,
            rollout_hook_url=None,
            rollback_hook_url=None,
            hook_bearer_token=None,
            hook_timeout_seconds=1,
            dry_run_hooks=False,
            fetch_sample_fn=fetch_sample_fn,
            sleep_fn=lambda _seconds: None,
        )
        self.assertTrue(passed)
        self.assertEqual(summary["total_samples"], 3)
        self.assertEqual(summary["failed_samples"], 0)
        self.assertEqual(summary["pass_samples"], 3)

    def test_run_canary_guard_triggers_rollback_hook_on_failure(self) -> None:
        calls: list[str] = []

        def fetch_sample_fn(**_kwargs):
            return False, ["ws_burn_rate_degraded"], {"ws": "ok", "ws_burn_rate": "degraded"}

        def hook_fn(**kwargs):
            calls.append(str(kwargs["action"]))

        passed, summary = run_canary_guard(
            health_url="https://example.com/health/slo",
            health_bearer_token=None,
            require_sufficient_data=False,
            duration_seconds=60,
            interval_seconds=30,
            max_failures=1,
            timeout_seconds=1,
            target_percent=1.0,
            rollout_hook_url="https://example.com/hooks/rollout",
            rollback_hook_url="https://example.com/hooks/rollback",
            hook_bearer_token=None,
            hook_timeout_seconds=1,
            dry_run_hooks=False,
            fetch_sample_fn=fetch_sample_fn,
            hook_fn=hook_fn,
            sleep_fn=lambda _seconds: None,
        )
        self.assertFalse(passed)
        self.assertEqual(summary["failed_samples"], 1)
        self.assertEqual(calls, ["rollout", "rollback"])

    def test_main_skips_when_missing_health_url_and_allow_flag(self) -> None:
        with patch.dict(
            "os.environ",
            {"CANARY_GUARD_HEALTH_SLO_URL": "", "SLO_GATE_HEALTH_SLO_URL": ""},
            clear=False,
        ):
            exit_code = main(["--allow-missing-health-url"])
        self.assertEqual(exit_code, 0)

    def test_main_fails_when_interval_greater_than_duration(self) -> None:
        exit_code = main(
            [
                "--health-url",
                "https://example.com/health/slo",
                "--duration-seconds",
                "30",
                "--interval-seconds",
                "60",
            ]
        )
        self.assertEqual(exit_code, 1)

    def test_main_passes_when_guard_result_is_success(self) -> None:
        with patch.object(
            _MODULE,
            "run_canary_guard",
            return_value=(True, {"total_samples": 1, "pass_samples": 1, "failed_samples": 0}),
        ):
            exit_code = main(["--health-url", "https://example.com/health/slo", "--dry-run-hooks"])
        self.assertEqual(exit_code, 0)

    def test_main_accepts_dry_run_hooks_and_allow_missing_health_url_rel_gate_02(self) -> None:
        """REL-GATE-02: Script must accept --dry-run-hooks and --allow-missing-health-url for CI without prod URL."""
        with patch.dict("os.environ", {"CANARY_GUARD_HEALTH_SLO_URL": "", "SLO_GATE_HEALTH_SLO_URL": ""}, clear=False):
            exit_code = main(["--dry-run-hooks", "--allow-missing-health-url"])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
