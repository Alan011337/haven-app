import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_env.py"
_SPEC = importlib.util.spec_from_file_location("check_env", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

main = _MODULE.main


def _required_env() -> dict[str, str]:
    return {
        "DATABASE_URL": "sqlite:///./test.db",
        "OPENAI_API_KEY": "test-key",
        "SECRET_KEY": "01234567890123456789012345678901",
    }


class BackendEnvCheckTests(unittest.TestCase):
    def _run_main(self, env_overrides: dict[str, str]) -> int:
        env = _required_env()
        env.update(env_overrides)
        with patch.object(
            _MODULE,
            "ENV_FILE",
            BACKEND_ROOT / "__codex_missing_env__.env",
        ), patch.dict("os.environ", env, clear=True):
            return main()

    def test_env_check_accepts_valid_ws_health_thresholds(self) -> None:
        exit_code = self._run_main(
            {
                "HEALTH_WS_CONNECTION_ACCEPT_RATE_TARGET": "0.995",
                "HEALTH_WS_MESSAGE_PASS_RATE_TARGET": "0.99",
                "HEALTH_WS_SLI_MIN_CONNECTION_ATTEMPTS": "50",
                "HEALTH_WS_SLI_MIN_MESSAGES": "100",
                "HEALTH_WS_BURN_RATE_FAST_THRESHOLD": "14.4",
                "HEALTH_WS_BURN_RATE_SLOW_THRESHOLD": "6.0",
                "HEALTH_WS_BURN_RATE_MIN_CONNECTION_ATTEMPTS": "20",
                "HEALTH_WS_BURN_RATE_MIN_MESSAGES": "40",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_accepts_local_postgres_when_local_dev_mode_enabled(self) -> None:
        exit_code = self._run_main(
            {
                "HAVEN_LOCAL_DEV_MODE": "1",
                "DATABASE_URL": "postgresql://haven:secret@127.0.0.1:55432/haven_local",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_remote_postgres_when_local_dev_mode_enabled(self) -> None:
        exit_code = self._run_main(
            {
                "HAVEN_LOCAL_DEV_MODE": "1",
                "DATABASE_URL": "postgresql://svc:secret@db.internal:5432/haven",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_rejects_sqlite_when_local_dev_mode_enabled(self) -> None:
        exit_code = self._run_main(
            {
                "HAVEN_LOCAL_DEV_MODE": "1",
                "DATABASE_URL": "sqlite:///./dev.db",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_rejects_read_replica_when_local_dev_mode_enabled(self) -> None:
        exit_code = self._run_main(
            {
                "HAVEN_LOCAL_DEV_MODE": "1",
                "DATABASE_READ_REPLICA_URL": "postgresql://replica.internal:5432/haven",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_rejects_ws_success_target_out_of_range(self) -> None:
        exit_code = self._run_main(
            {
                "HEALTH_WS_CONNECTION_ACCEPT_RATE_TARGET": "1.1",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_rejects_burn_rate_fast_lower_than_slow(self) -> None:
        exit_code = self._run_main(
            {
                "HEALTH_WS_BURN_RATE_FAST_THRESHOLD": "3",
                "HEALTH_WS_BURN_RATE_SLOW_THRESHOLD": "6",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_existing_slo_payload_file(self) -> None:
        exit_code = self._run_main(
            {
                "SLO_GATE_HEALTH_SLO_FILE": "tests/test_slo_burn_rate_gate.py",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_missing_slo_payload_file(self) -> None:
        exit_code = self._run_main(
            {
                "SLO_GATE_HEALTH_SLO_FILE": "tests/__missing_slo_snapshot__.json",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_valid_canary_guard_config(self) -> None:
        exit_code = self._run_main(
            {
                "CANARY_GUARD_HEALTH_SLO_URL": "https://example.com/health/slo",
                "CANARY_GUARD_DURATION_SECONDS": "300",
                "CANARY_GUARD_INTERVAL_SECONDS": "30",
                "CANARY_GUARD_MAX_FAILURES": "2",
                "CANARY_GUARD_TIMEOUT_SECONDS": "10",
                "CANARY_GUARD_TARGET_PERCENT": "5",
                "CANARY_GUARD_ROLLOUT_HOOK_URL": "https://example.com/hooks/rollout",
                "CANARY_GUARD_ROLLBACK_HOOK_URL": "https://example.com/hooks/rollback",
                "CANARY_GUARD_HOOK_TIMEOUT_SECONDS": "10",
                "CANARY_GUARD_REQUIRE_SUFFICIENT_DATA": "true",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_canary_guard_interval_above_duration(self) -> None:
        exit_code = self._run_main(
            {
                "CANARY_GUARD_DURATION_SECONDS": "30",
                "CANARY_GUARD_INTERVAL_SECONDS": "60",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_valid_p0_drill_evidence_max_age_days(self) -> None:
        exit_code = self._run_main(
            {
                "P0_DRILL_EVIDENCE_MAX_AGE_DAYS": "35",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_p0_drill_evidence_max_age_days(self) -> None:
        exit_code = self._run_main(
            {
                "P0_DRILL_EVIDENCE_MAX_AGE_DAYS": "0",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_valid_billing_and_audit_evidence_max_age_days(self) -> None:
        exit_code = self._run_main(
            {
                "BILLING_RECON_EVIDENCE_MAX_AGE_DAYS": "14",
                "AUDIT_RETENTION_EVIDENCE_MAX_AGE_DAYS": "14",
                "DATA_EXPORT_EXPIRY_DAYS": "7",
                "LAUNCH_SIGNOFF_MAX_AGE_DAYS": "14",
                "CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS": "36",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_billing_and_audit_evidence_max_age_days(self) -> None:
        exit_code = self._run_main(
            {
                "BILLING_RECON_EVIDENCE_MAX_AGE_DAYS": "-1",
                "AUDIT_RETENTION_EVIDENCE_MAX_AGE_DAYS": "abc",
                "DATA_EXPORT_EXPIRY_DAYS": "0",
                "LAUNCH_SIGNOFF_MAX_AGE_DAYS": "0",
                "CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS": "-5",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_valid_release_gate_override_flags(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_ALLOW_MISSING_SLO_URL": "false",
                "RELEASE_GATE_ALLOW_MISSING_LAUNCH_SIGNOFF": "1",
                "RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE": "true",
                "RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE": "yes",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_accepts_valid_release_gate_ai_quality_evidence_source(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE": "daily_artifact",
                "RELEASE_GATE_AI_QUALITY_EVIDENCE_REPO": "acme/haven",
                "RELEASE_GATE_AI_QUALITY_EVIDENCE_BRANCH": "main",
                "RELEASE_GATE_AI_QUALITY_EVIDENCE_ARTIFACT_NAME": "ai-quality-snapshot",
                "RELEASE_GATE_AI_QUALITY_EVIDENCE_ARTIFACT_FILE": "docs/security/evidence/ai-quality-snapshot-latest.json",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_release_gate_override_flags(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_ALLOW_MISSING_SLO_URL": "maybe",
                "RELEASE_GATE_ALLOW_MISSING_LAUNCH_SIGNOFF": "sometimes",
                "RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE": "2",
                "RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE": "enable",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_rejects_invalid_release_gate_ai_quality_evidence_source(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE": "remote",
                "RELEASE_GATE_AI_QUALITY_EVIDENCE_REPO": "invalid-format",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_valid_release_gate_hotfix_override_fields(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_HOTFIX_OVERRIDE": "true",
                "RELEASE_GATE_OVERRIDE_REASON": "prod-incident-hotfix",
                "RELEASE_GATE_OVERRIDE_REASON_PATTERN": r"^[A-Za-z0-9._-]{3,128}$",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_accepts_valid_ai_router_shared_state_redis_config(self) -> None:
        exit_code = self._run_main(
            {
                "AI_ROUTER_SHARED_STATE_BACKEND": "redis",
                "AI_ROUTER_REDIS_URL": "redis://redis.internal:6379/0",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_ai_router_shared_state_backend(self) -> None:
        exit_code = self._run_main(
            {
                "AI_ROUTER_SHARED_STATE_BACKEND": "postgres",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_rejects_missing_ai_router_redis_url_when_backend_is_redis(self) -> None:
        exit_code = self._run_main(
            {
                "AI_ROUTER_SHARED_STATE_BACKEND": "redis",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_abuse_guard_redis_url_as_ai_router_shared_state_fallback(self) -> None:
        exit_code = self._run_main(
            {
                "AI_ROUTER_SHARED_STATE_BACKEND": "redis",
                "ABUSE_GUARD_REDIS_URL": "redis://redis.internal:6379/1",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_release_gate_hotfix_override_fields(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_GATE_HOTFIX_OVERRIDE": "enable",
                "RELEASE_GATE_OVERRIDE_REASON": "x" * 301,
                "RELEASE_GATE_OVERRIDE_REASON_PATTERN": "[bad-regex",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_valid_release_target_tier_and_release_intent(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_TARGET_TIER": "tier_1",
                "RELEASE_INTENT": "feature",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_release_target_tier_and_release_intent(self) -> None:
        exit_code = self._run_main(
            {
                "RELEASE_TARGET_TIER": "tier_x",
                "RELEASE_INTENT": "deploy",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_valid_ai_dynamic_context_injection_flag(self) -> None:
        exit_code = self._run_main(
            {
                "AI_DYNAMIC_CONTEXT_INJECTION_ENABLED": "true",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_ai_dynamic_context_injection_flag(self) -> None:
        exit_code = self._run_main(
            {
                "AI_DYNAMIC_CONTEXT_INJECTION_ENABLED": "enable",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_valid_ai_persona_runtime_guardrail_flag(self) -> None:
        exit_code = self._run_main(
            {
                "AI_PERSONA_RUNTIME_GUARDRAIL_ENABLED": "true",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_ai_persona_runtime_guardrail_flag(self) -> None:
        exit_code = self._run_main(
            {
                "AI_PERSONA_RUNTIME_GUARDRAIL_ENABLED": "enable",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_valid_ai_router_config(self) -> None:
        exit_code = self._run_main(
            {
                "AI_ROUTER_PRIMARY_PROVIDER": "openai",
                "AI_ROUTER_FALLBACK_PROVIDER": "gemini",
                "AI_ROUTER_ENABLE_FALLBACK": "true",
                "GEMINI_API_KEY": "gemini-test-key",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_ai_router_config(self) -> None:
        exit_code = self._run_main(
            {
                "AI_ROUTER_PRIMARY_PROVIDER": "anthropic",
                "AI_ROUTER_FALLBACK_PROVIDER": "none",
                "AI_ROUTER_ENABLE_FALLBACK": "maybe",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_rejects_missing_gemini_key_when_router_uses_gemini(self) -> None:
        exit_code = self._run_main(
            {
                "AI_ROUTER_PRIMARY_PROVIDER": "gemini",
                "AI_ROUTER_ENABLE_FALLBACK": "false",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_valid_ai_cost_quality_config(self) -> None:
        exit_code = self._run_main(
            {
                "AI_SCHEMA_COMPLIANCE_MIN": "99.9",
                "AI_HALLUCINATION_PROXY_MAX": "0.05",
                "AI_DRIFT_SCORE_MAX": "0.2",
                "AI_COST_MAX_USD_PER_ACTIVE_COUPLE": "1.5",
                "AI_TOKEN_BUDGET_DAILY": "2000000",
                "AI_QUALITY_SNAPSHOT_MAX_AGE_HOURS": "36",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_ai_cost_quality_config(self) -> None:
        exit_code = self._run_main(
            {
                "AI_SCHEMA_COMPLIANCE_MIN": "110",
                "AI_HALLUCINATION_PROXY_MAX": "1.5",
                "AI_DRIFT_SCORE_MAX": "0",
                "AI_COST_MAX_USD_PER_ACTIVE_COUPLE": "-1",
                "AI_TOKEN_BUDGET_DAILY": "0",
                "AI_QUALITY_SNAPSHOT_MAX_AGE_HOURS": "0",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_valid_soft_delete_phase_gate_env(self) -> None:
        exit_code = self._run_main(
            {
                "DATA_SOFT_DELETE_ENABLED": "false",
                "DATA_SOFT_DELETE_TRASH_RETENTION_DAYS": "30",
                "DATA_SOFT_DELETE_PURGE_RETENTION_DAYS": "90",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_soft_delete_enabled_flag(self) -> None:
        exit_code = self._run_main(
            {
                "DATA_SOFT_DELETE_ENABLED": "maybe",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_rejects_soft_delete_purge_days_lower_than_trash_days(self) -> None:
        exit_code = self._run_main(
            {
                "DATA_SOFT_DELETE_TRASH_RETENTION_DAYS": "30",
                "DATA_SOFT_DELETE_PURGE_RETENTION_DAYS": "7",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_valid_soft_delete_purge_evidence_max_age_days(self) -> None:
        exit_code = self._run_main(
            {
                "DATA_SOFT_DELETE_PURGE_EVIDENCE_MAX_AGE_DAYS": "14",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_soft_delete_purge_evidence_max_age_days(self) -> None:
        exit_code = self._run_main(
            {
                "DATA_SOFT_DELETE_PURGE_EVIDENCE_MAX_AGE_DAYS": "0",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_field_level_encryption_config(self) -> None:
        exit_code = self._run_main(
            {
                "FIELD_LEVEL_ENCRYPTION_ENABLED": "true",
                "FIELD_LEVEL_ENCRYPTION_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_invalid_field_level_encryption_key(self) -> None:
        exit_code = self._run_main(
            {
                "FIELD_LEVEL_ENCRYPTION_ENABLED": "true",
                "FIELD_LEVEL_ENCRYPTION_KEY": "invalid-key",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_requires_field_level_encryption_in_production(self) -> None:
        exit_code = self._run_main(
            {
                "ENV": "production",
                "FIELD_LEVEL_ENCRYPTION_ENABLED": "false",
            }
        )
        self.assertEqual(exit_code, 1)

    def test_env_check_accepts_matching_env_and_environment_alias(self) -> None:
        exit_code = self._run_main(
            {
                "ENV": "prod",
                "ENVIRONMENT": "production",
                "FIELD_LEVEL_ENCRYPTION_ENABLED": "true",
                "FIELD_LEVEL_ENCRYPTION_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            }
        )
        self.assertEqual(exit_code, 0)

    def test_env_check_rejects_mismatched_env_and_environment(self) -> None:
        exit_code = self._run_main(
            {
                "ENV": "alpha",
                "ENVIRONMENT": "production",
            }
        )
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
