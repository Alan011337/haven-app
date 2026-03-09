import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

RELEASE_GATE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release-gate.yml"
RELEASE_GATE_SCRIPT_PATH = REPO_ROOT / "scripts" / "release-gate.sh"
RELEASE_GATE_LOCAL_SCRIPT_PATH = REPO_ROOT / "scripts" / "release-gate-local.sh"
E2E_SUMMARY_SCRIPT_PATH = REPO_ROOT / "frontend" / "scripts" / "summarize-e2e-result.mjs"
E2E_SUMMARY_SCHEMA_GATE_SCRIPT_PATH = (
    REPO_ROOT / "frontend" / "scripts" / "check-e2e-summary-schema.mjs"
)
SECURITY_EVIDENCE_REFRESH_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "security-evidence-refresh.yml"
)


class ReleaseGateWorkflowContractTests(unittest.TestCase):
    def test_release_gate_workflow_runs_api_contract_snapshot_gate(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: API contract snapshot gate (fail-closed)", text)
        self.assertIn("python scripts/check_api_contract_snapshot.py", text)

    def test_release_gate_workflow_enforces_test_profile_sla(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Backend test profile SLA gate (smoke)", text)
        self.assertIn("./scripts/run-test-profile.sh smoke", text)
        self.assertIn("TEST_PROFILE_SLA_ENFORCED", text)

    def test_release_gate_workflow_contains_deploy_preflight_gate_steps(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn('SECRET_KEY: "01234567890123456789012345678901"', text)
        self.assertIn('PYTHONUTF8: "1"', text)
        self.assertIn("PYTHONPATH: .", text)
        self.assertIn("name: Setup Flyctl for deploy preflight", text)
        self.assertIn("superfly/flyctl-actions/setup-flyctl@master", text)
        self.assertIn("version: '0.3.221'", text)
        self.assertIn("name: Deploy preflight gate (PR optional)", text)
        self.assertIn("name: Deploy preflight gate (main required)", text)
        self.assertIn("FLY_DEPLOY_PREFLIGHT_ONLY: \"1\"", text)
        self.assertIn("FLY_APP_NAME: ${{ vars.FLY_APP_NAME || 'haven-api-prod' }}", text)
        self.assertIn("bash ../scripts/deploy-fly-backend.sh", text)
        self.assertIn("[deploy-preflight] skipped: missing FLY_API_TOKEN", text)

    def test_release_gate_workflow_contains_timeline_perf_baseline_gate(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Timeline perf baseline gate (PR internal required)", text)
        self.assertIn("name: Timeline perf baseline gate (PR fork optional)", text)
        self.assertIn("name: Timeline perf baseline gate (main required)", text)
        self.assertIn("name: Timeline perf baseline gate summary", text)
        self.assertIn("python scripts/run_perf_baseline.py", text)
        self.assertIn("python scripts/check_timeline_perf_baseline_gate.py", text)
        self.assertIn("--timeline-p95-budget-ms 300", text)
        self.assertIn("--fail-on-degraded", text)

    def test_release_gate_workflow_includes_cuj_synthetic_evidence_steps(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: CUJ synthetic evidence gate (PR optional)", text)
        self.assertIn("name: CUJ synthetic evidence gate (main required)", text)
        self.assertIn("name: CUJ synthetic evidence gate summary", text)
        self.assertIn(
            "python scripts/check_cuj_synthetic_evidence_gate.py --allow-missing-evidence --require-pass --max-age-hours 36 --summary-path /tmp/cuj-synthetic-evidence-summary.json",
            text,
        )
        self.assertIn(
            "python scripts/check_cuj_synthetic_evidence_gate.py --require-pass --max-age-hours 36 --summary-path /tmp/cuj-synthetic-evidence-summary.json",
            text,
        )

    def test_release_gate_workflow_main_launch_signoff_requires_ready(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Launch signoff artifact gate (main required)", text)
        self.assertIn("if: github.ref == 'refs/heads/main'", text)
        self.assertIn(
            "python scripts/check_launch_signoff_gate.py --require-ready --max-age-days 14 --summary-path /tmp/launch-signoff-gate-summary.json",
            text,
        )

    def test_release_gate_workflow_summary_emits_key_fields(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("### CUJ synthetic evidence gate", text)
        self.assertIn("failure_class", text)
        self.assertIn("evidence_result", text)
        self.assertIn("evidence_age_hours", text)
        self.assertIn('Path("/tmp/cuj-synthetic-evidence-summary.json")', text)

    def test_release_gate_script_contains_cuj_synthetic_evidence_fail_closed_path(self) -> None:
        text = RELEASE_GATE_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE", text)
        self.assertIn("cuj synthetic evidence gate: fail-closed", text)
        self.assertIn("scripts/check_cuj_synthetic_evidence_gate.py", text)
        self.assertIn("--require-pass", text)
        self.assertIn("--max-age-hours", text)

    def test_release_gate_script_checks_env_secret_manifest_contract(self) -> None:
        text = RELEASE_GATE_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("scripts/check_env.py", text)
        self.assertIn("scripts/check_env_secret_manifest_contract.py", text)
        self.assertIn('export FLY_APP_NAME="${FLY_APP_NAME:-haven-api-prod}"', text)
        self.assertIn(
            'export SLO_GATE_HEALTH_SLO_URL="https://${FLY_APP_NAME}.fly.dev/health/slo"',
            text,
        )
        self.assertIn("defaulted SLO_GATE_HEALTH_SLO_URL from FLY_APP_NAME", text)
        self.assertIn('require_release_env_var "FLY_API_TOKEN"', text)
        self.assertIn('require_release_env_var "CORS_ORIGINS"', text)
        self.assertIn("missing required deploy env", text)
        self.assertIn("deploy preflight gate: fail-closed", text)
        self.assertIn('env FLY_DEPLOY_PREFLIGHT_ONLY=1', text)
        self.assertIn('scripts/deploy-fly-backend.sh', text)
        self.assertIn("scripts/run_with_timeout.py", text)
        self.assertIn("run_shell_gate_step", text)
        self.assertIn('E2E_NODE_BIN="${E2E_NODE_BIN:-node}"', text)
        self.assertIn('E2E_EXEC_PATH="${PATH}"', text)
        self.assertIn('E2E_NODE_BIN="/opt/homebrew/opt/node@22/bin/node"', text)
        self.assertIn('E2E_PROJECT_BROWSERS_PATH="${ROOT_DIR}/frontend/.playwright-browsers"', text)
        self.assertIn("reusing frontend Playwright browser cache", text)
        self.assertIn("playwright browsers path", text)
        self.assertIn('PATH="${E2E_EXEC_PATH}"', text)
        self.assertIn('PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-}"', text)

    def test_release_gate_script_requires_launch_signoff_ready(self) -> None:
        text = RELEASE_GATE_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("scripts/check_launch_signoff_gate.py", text)
        self.assertIn("--require-ready", text)

    def test_release_gate_script_requires_hotfix_fields_for_relaxations(self) -> None:
        text = RELEASE_GATE_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("scripts/check_release_gate_override_contract.py", text)
        self.assertIn("/tmp/release-gate-override-summary.json", text)
        self.assertIn("RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE", text)

    def test_release_gate_script_writes_slo_burn_rate_summary(self) -> None:
        text = RELEASE_GATE_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("SLO_BURN_RATE_SUMMARY_PATH", text)
        self.assertIn("check_slo_burn_rate_gate.py", text)
        self.assertIn("--summary-path", text)

    def test_release_gate_scripts_include_service_tier_budget_gate(self) -> None:
        workflow_text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        release_gate_text = RELEASE_GATE_SCRIPT_PATH.read_text(encoding="utf-8")
        local_text = RELEASE_GATE_LOCAL_SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("name: Service tier budget gate (PR optional)", workflow_text)
        self.assertIn("name: Service tier budget gate (main required)", workflow_text)
        self.assertIn("name: Service tier budget gate summary", workflow_text)
        self.assertIn("python scripts/check_service_tier_budget_gate.py", workflow_text)
        self.assertIn("### Service tier budget gate", workflow_text)
        self.assertIn("target_tier", workflow_text)
        self.assertIn("release_intent", workflow_text)
        self.assertIn("tier_error_budget_freeze_enforced", workflow_text)

        self.assertIn("scripts/check_service_tier_budget_gate.py", release_gate_text)
        self.assertIn("service tier summary", release_gate_text)

        self.assertIn("scripts/check_service_tier_budget_gate.py", local_text)
        self.assertIn("service tier summary", local_text)

    def test_release_gate_script_supports_daily_ai_quality_artifact_source(self) -> None:
        text = RELEASE_GATE_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE", text)
        self.assertIn("daily_artifact", text)
        self.assertIn("local_snapshot", text)
        self.assertIn("scripts/fetch_latest_ai_quality_snapshot_evidence.py", text)
        self.assertIn("scripts/run_ai_quality_snapshot.py", text)
        self.assertIn("RELEASE_GATE_AI_QUALITY_EVIDENCE_WORKFLOW_FILE", text)

    def test_release_gate_script_emits_ai_quality_source_and_gate_summaries(self) -> None:
        text = RELEASE_GATE_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("AI_QUALITY_FETCH_SUMMARY_PATH", text)
        self.assertIn("AI_QUALITY_GATE_SUMMARY_PATH", text)
        self.assertIn("ai quality summary", text)
        self.assertIn("source_result", text)
        self.assertIn("gate_result", text)
        self.assertIn("scripts/run_core_loop_snapshot.py", text)
        self.assertIn("CORE_LOOP_SNAPSHOT_DATABASE_URL", text)
        self.assertIn("core loop snapshot summary", text)
        self.assertIn("non_blocking_on_degraded", text)
        self.assertIn("scripts/build_gate_orchestration_summary.py", text)
        self.assertIn("release-gate-orchestration-summary.json", text)
        self.assertIn("gate orchestration summary", text)

    def test_release_gate_workflow_contains_hotfix_override_contract_steps(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Release gate hotfix override contract (PR optional)", text)
        self.assertIn("name: Release gate hotfix override contract (main required)", text)
        self.assertIn("name: Release gate hotfix override contract summary", text)
        self.assertIn("python scripts/check_release_gate_override_contract.py", text)
        self.assertIn("### Release gate hotfix override contract", text)
        self.assertIn("override_reason_present", text)
        self.assertIn("override_reason_pattern", text)
        self.assertIn("override_reason", text)
        self.assertIn("enabled_relaxations", text)
        self.assertIn("RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE", text)
        self.assertIn("RELEASE_GATE_OVERRIDE_REASON_PATTERN", text)

    def test_release_gate_workflow_main_slo_gate_is_fail_closed_without_sufficient_data_override(
        self,
    ) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: SLO burn-rate gate (main required)", text)
        self.assertIn(
            "python scripts/check_slo_burn_rate_gate.py --summary-path /tmp/slo-burn-rate-gate-summary.json",
            text,
        )
        self.assertNotIn(
            "python scripts/check_slo_burn_rate_gate.py --require-sufficient-data --summary-path /tmp/slo-burn-rate-gate-summary.json",
            text,
        )
        self.assertIn("name: Observability live contract gate (PR internal optional)", text)
        self.assertIn("name: Observability live contract gate (main required)", text)
        self.assertIn("python scripts/check_observability_live_contract.py", text)
        self.assertIn("ai_router_burn_rate_status", text)

    def test_release_gate_script_defaults_slo_sufficient_data_to_monitor_mode(self) -> None:
        text = RELEASE_GATE_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn(
            'RELEASE_GATE_REQUIRE_SLO_SUFFICIENT_DATA="${RELEASE_GATE_REQUIRE_SLO_SUFFICIENT_DATA:-0}"',
            text,
        )
        self.assertIn("slo burn-rate gate: monitor insufficient_data", text)

    def test_release_gate_workflow_main_hotfix_contract_is_fail_closed(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("- name: Release gate hotfix override contract (main required)", text)
        self.assertIn("if: github.ref == 'refs/heads/main'", text)
        self.assertIn(
            "run: python scripts/check_release_gate_override_contract.py --summary-path /tmp/release-gate-override-summary.json",
            text,
        )
        self.assertNotIn(
            "check_release_gate_override_contract.py --allow-missing",
            text,
        )

    def test_release_gate_workflow_contains_ai_quality_snapshot_freshness_gate_steps(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Fetch latest AI quality snapshot evidence (daily artifact)", text)
        self.assertIn("name: AI quality snapshot freshness gate (PR optional)", text)
        self.assertIn("name: AI quality snapshot freshness gate (main required)", text)
        self.assertIn("name: AI quality snapshot freshness gate summary", text)
        self.assertIn("python scripts/fetch_latest_ai_quality_snapshot_evidence.py", text)
        self.assertIn("python scripts/check_ai_quality_snapshot_freshness_gate.py --evidence /tmp/ai-quality-snapshot-latest.json", text)
        self.assertIn("--allow-missing-evidence", text)
        self.assertIn("non_blocking_on_degraded", text)
        self.assertIn("evidence_source_result", text)
        self.assertIn("evidence_source_run_id", text)
        self.assertIn("evidence_source_artifact_id", text)

    def test_release_gate_local_script_contains_cuj_synthetic_evidence_fail_closed_default(self) -> None:
        text = RELEASE_GATE_LOCAL_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE", text)
        self.assertIn("cuj synthetic evidence gate: fail-closed", text)
        self.assertIn("cuj synthetic evidence gate: override enabled (allow missing evidence)", text)
        self.assertIn("--require-pass", text)
        self.assertIn("--allow-missing-evidence", text)
        self.assertIn("scripts/check_cuj_synthetic_evidence_gate.py", text)

    def test_local_cuj_synthetic_fixture_contains_sufficient_data_slo_statuses(self) -> None:
        text = (REPO_ROOT / "scripts" / "generate-cuj-synthetic-evidence-local.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('"ai_router_burn_rate": {"status": "ok"}', text)
        self.assertIn('"push": {"status": "ok"}', text)
        self.assertIn('"cuj": {"status": "ok"}', text)
        self.assertIn('"abuse_economics": {', text)
        self.assertIn('"evaluation": {"status": "ok"}', text)
        self.assertNotIn('"cuj": {"status": "insufficient_data"}', text)

    def test_release_gate_local_script_supports_security_profile_and_inventory_autowrite(self) -> None:
        text = RELEASE_GATE_LOCAL_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("run_local_backend_contract_preflight_steps()", text)
        self.assertIn("run_local_api_contract_alignment_steps()", text)
        self.assertIn("scripts/check_frontend_security_headers_contract.py", text)
        self.assertIn("scripts/check_event_registry_contract.py", text)
        self.assertIn("scripts/check_env_secret_manifest_contract.py", text)
        self.assertIn("scripts/run_with_timeout.py", text)
        self.assertIn("RELEASE_GATE_SECURITY_PROFILE", text)
        self.assertIn('RELEASE_GATE_SECURITY_PROFILE="fast"', text)
        self.assertIn('RELEASE_GATE_SECURITY_PROFILE="full"', text)
        self.assertIn("API_INVENTORY_AUTO_WRITE", text)
        self.assertIn("SECURITY_GATE_PROFILE=", text)
        self.assertIn("api inventory auto-write", text)

    def test_release_gate_local_script_slo_missing_url_can_be_fail_closed(self) -> None:
        text = RELEASE_GATE_LOCAL_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("RELEASE_GATE_ENV", text)
        self.assertIn("env mode", text)
        self.assertIn("release_gate_component_kind", text)
        self.assertIn("RELEASE_GATE_DATA_RETENTION_DATABASE_URL", text)
        self.assertIn("sqlite:///./test.db", text)
        self.assertIn("RELEASE_GATE_PROTECTED_BRANCH", text)
        self.assertIn("protected branch mode", text)
        self.assertIn("release_gate_default_by_strict_mode", text)
        self.assertIn("RELEASE_GATE_AUTO_REFRESH_EVIDENCE", text)
        self.assertIn('RELEASE_GATE_AUTO_REFRESH_EVIDENCE="0"', text)
        self.assertIn("scripts/refresh-security-evidence-local.sh", text)
        self.assertIn("RELEASE_GATE_ALLOW_MISSING_SLO_URL", text)
        self.assertIn('RELEASE_GATE_ALLOW_MISSING_SLO_URL="0"', text)
        self.assertIn("no URL/file configured; generating local CUJ fixture", text)
        self.assertIn("SLO_GATE_HEALTH_SLO_FILE", text)
        self.assertIn("slo burn-rate gate: allow missing URL", text)
        self.assertIn("slo burn-rate gate: fail-closed (missing URL not allowed)", text)
        self.assertIn("check_slo_burn_rate_gate.py", text)
        self.assertIn("--allow-missing-url", text)
        self.assertIn('scripts/check_slo_burn_rate_gate.py', text)
        self.assertIn("RELEASE_GATE_ALLOW_MISSING_ERROR_BUDGET_STATUS", text)
        self.assertIn("error budget gate: fail-closed", text)
        self.assertIn("RELEASE_GATE_ALLOW_MISSING_SERVICE_TIER_STATUS", text)
        self.assertIn("service tier gate: fail-closed", text)
        self.assertIn("RELEASE_GATE_ALLOW_DEGRADED_AI_RUNTIME", text)
        self.assertIn("RELEASE_GATE_CORE_LOOP_FAIL_ON_DEGRADED", text)

    def test_security_evidence_refresh_workflow_runs_core_local_refresh_steps(self) -> None:
        text = SECURITY_EVIDENCE_REFRESH_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Security Evidence Refresh", text)
        self.assertIn("workflow_dispatch", text)
        self.assertIn("schedule:", text)
        self.assertIn("bash scripts/generate-cuj-synthetic-evidence-local.sh", text)
        self.assertIn("bash scripts/billing-reconciliation.sh", text)
        self.assertIn("bash scripts/audit-log-retention.sh", text)

    def test_release_gate_local_script_requires_launch_signoff_ready(self) -> None:
        text = RELEASE_GATE_LOCAL_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("RELEASE_GATE_ALLOW_MISSING_LAUNCH_SIGNOFF", text)
        self.assertIn("launch signoff gate: fail-closed", text)
        self.assertIn("launch signoff gate: override enabled (allow missing artifact)", text)
        self.assertIn("scripts/check_launch_signoff_gate.py", text)
        self.assertIn("--require-ready", text)
        self.assertIn("scripts/check_release_gate_override_contract.py", text)
        self.assertIn("/tmp/release-gate-override-summary-local.json", text)

    def test_release_gate_local_script_emits_frontend_e2e_summary_contract(self) -> None:
        text = RELEASE_GATE_LOCAL_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("strict mode: enabling frontend e2e by default", text)
        self.assertIn("RELEASE_GATE_E2E_NODE_BIN", text)
        self.assertIn("strict mode: reusing detected Homebrew Node 22 for frontend e2e", text)
        self.assertIn("/opt/homebrew/opt/node@22/bin/node", text)
        self.assertIn("E2E_NODE_SOURCE", text)
        self.assertIn("E2E_EXEC_PATH", text)
        self.assertIn("E2E_PROJECT_BROWSERS_PATH", text)
        self.assertIn("reusing frontend Playwright browser cache", text)
        self.assertIn("RUN_E2E=1 is not supported on Node", text)
        self.assertIn("use Node 20 or 22", text)
        self.assertIn("E2E_BASE_URL not set; relying on Playwright local webServer.", text)
        self.assertIn("E2E_WEB_SERVER_COMMAND", text)
        self.assertIn("./node_modules/.bin/next dev --webpack -H 127.0.0.1 --port 3000", text)
        self.assertIn("e2e runtime mode", text)
        self.assertIn("e2e node source", text)
        self.assertIn("e2e node binary", text)
        self.assertIn("e2e node version", text)
        self.assertIn("e2e browser cache source", text)
        self.assertIn("e2e web server command", text)
        self.assertIn("frontend_project_cache", text)
        self.assertIn("tmp_release_gate_cache", text)
        self.assertIn("playwright_managed_local_web_server", text)
        self.assertIn("E2E_ALLOW_BROWSER_DOWNLOAD_FAILURE", text)
        self.assertIn("E2E_SUMMARY_PATH", text)
        self.assertIn("E2E_TIMEOUT_SECONDS", text)
        self.assertIn("E2E_TIMEOUT_GRACE_SECONDS", text)
        self.assertIn("RUN_QUICK_BACKEND_CONTRACT_TESTS", text)
        self.assertIn("running quick backend contract tests", text)
        self.assertIn("QUICK_BACKEND_CONTRACT_LOG_PATH", text)
        self.assertIn("QUICK_BACKEND_CONTRACT_SUMMARY_PATH", text)
        self.assertIn("quick backend contract summary", text)
        self.assertIn("scripts/check_quick_backend_contract_summary.py", text)
        self.assertIn('"schema_version": "v1"', text)
        self.assertIn('"duration_seconds"', text)
        self.assertIn("Frontend e2e smoke (skipped)", text)
        self.assertIn("--exit-code \"nan\"", text)
        self.assertIn("tests/test_frontend_e2e_summary_schema_gate_script.py", text)
        self.assertIn("tests/test_frontend_e2e_summary_contract.py", text)
        self.assertIn("tests/test_frontend_e2e_summary_script.py", text)
        self.assertIn("tests/test_security_gate_contract.py", text)
        self.assertIn("scripts/run-e2e-with-timeout.mjs", text)
        self.assertIn("scripts/summarize-e2e-result.mjs", text)
        self.assertIn("scripts/check-e2e-summary-schema.mjs", text)
        self.assertIn("--required-schema-version v1", text)
        self.assertIn("browser_download_network", text)
        self.assertIn("e2e degraded: browser download network failure", text)

    def test_release_gate_local_script_supports_daily_ai_quality_artifact_source(self) -> None:
        text = RELEASE_GATE_LOCAL_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE", text)
        self.assertIn("daily_artifact", text)
        self.assertIn("local_snapshot", text)
        self.assertIn("scripts/fetch_latest_ai_quality_snapshot_evidence.py", text)
        self.assertIn("scripts/run_ai_quality_snapshot.py", text)
        self.assertIn("RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE", text)

    def test_release_gate_local_script_emits_ai_quality_source_and_gate_summaries(self) -> None:
        text = RELEASE_GATE_LOCAL_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("AI_QUALITY_FETCH_SUMMARY_PATH", text)
        self.assertIn("AI_QUALITY_GATE_SUMMARY_PATH", text)
        self.assertIn("--summary-path", text)
        self.assertIn("ai quality summary", text)
        self.assertIn("source_result", text)
        self.assertIn("gate_result", text)
        self.assertIn("evaluation_result", text)
        self.assertIn("scripts/run_core_loop_snapshot.py", text)
        self.assertIn("CORE_LOOP_SNAPSHOT_DATABASE_URL", text)
        self.assertIn("core loop snapshot summary", text)
        self.assertIn("non_blocking_on_degraded", text)
        self.assertIn("scripts/check_timeline_runtime_alert_gate.py", text)
        self.assertIn("TIMELINE_RUNTIME_SUMMARY_PATH", text)
        self.assertIn("timeline_runtime", text)
        self.assertIn("scripts/run_notification_outbox_health_snapshot.py", text)
        self.assertIn("OUTBOX_HEALTH_SUMMARY_PATH", text)
        self.assertIn("outbox_health", text)
        self.assertIn("scripts/build_gate_orchestration_summary.py", text)
        self.assertIn("release-gate-orchestration-summary-local.json", text)
        self.assertIn("gate orchestration summary", text)
        self.assertIn("RELEASE_GATE_CLEAN_EVIDENCE_NOISE", text)
        self.assertIn("scripts/clean-evidence-noise.sh", text)
        self.assertIn("evidence noise cleanup", text)
        self.assertIn("scripts/check_api_contract_snapshot.py", text)
        self.assertIn("API_CONTRACT_SNAPSHOT_SUMMARY_PATH", text)
        self.assertIn("api_contract_snapshot", text)
        self.assertIn("scripts/run_ai_router_multinode_stress.py", text)
        self.assertIn("RELEASE_GATE_RUN_AI_ROUTER_STRESS", text)

    def test_release_gate_workflow_contains_core_loop_snapshot_gate_steps(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Core loop snapshot gate (PR optional)", text)
        self.assertIn("name: Core loop snapshot gate (main required)", text)
        self.assertIn("name: Core loop snapshot gate summary", text)
        self.assertIn("python scripts/run_core_loop_snapshot.py", text)
        self.assertIn("--output /tmp/core-loop-snapshot-latest.json", text)
        self.assertIn("--latest-path /tmp/core-loop-snapshot-latest.json", text)
        self.assertIn("### Core loop snapshot gate", text)
        self.assertIn("non_blocking_on_degraded", text)

    def test_release_gate_local_script_seeds_core_loop_fixture_db_by_default(self) -> None:
        text = RELEASE_GATE_LOCAL_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("CORE_LOOP_SNAPSHOT_FIXTURE_DATABASE_URL", text)
        self.assertIn("core loop snapshot: seeding local fixture db", text)
        self.assertIn("scripts/seed_core_loop_fixture.py", text)
        self.assertIn("--database-url", text)
        self.assertIn("--reset", text)

    def test_release_gate_scripts_include_ai_quality_snapshot_freshness_checks(self) -> None:
        workflow_text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        release_gate_text = RELEASE_GATE_SCRIPT_PATH.read_text(encoding="utf-8")
        local_text = RELEASE_GATE_LOCAL_SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("scripts/fetch_latest_ai_quality_snapshot_evidence.py", workflow_text)
        self.assertIn("scripts/check_ai_quality_snapshot_freshness_gate.py", workflow_text)
        self.assertIn("scripts/run_ai_quality_snapshot.py", release_gate_text)
        self.assertIn("scripts/check_ai_quality_snapshot_freshness_gate.py", release_gate_text)
        self.assertIn("scripts/fetch_latest_ai_quality_snapshot_evidence.py", local_text)
        self.assertIn("scripts/run_ai_quality_snapshot.py", local_text)
        self.assertIn("scripts/check_ai_quality_snapshot_freshness_gate.py", local_text)

    def test_release_gate_workflow_frontend_e2e_has_playwright_cache_contract(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("frontend-e2e:", text)
        self.assertIn(
            "continue-on-error: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository }}",
            text,
        )
        self.assertIn(
            "PLAYWRIGHT_BROWSERS_PATH: ${{ github.workspace }}/frontend/.playwright-browsers",
            text,
        )
        self.assertIn("name: Cache Playwright browsers", text)
        self.assertIn("uses: actions/cache@v4", text)
        self.assertIn("path: ${{ env.PLAYWRIGHT_BROWSERS_PATH }}", text)
        self.assertIn("hashFiles('frontend/package-lock.json')", text)

    def test_release_gate_script_has_node_version_guard_for_e2e(self) -> None:
        text = RELEASE_GATE_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("RUN_E2E=1 is not supported on Node", text)
        self.assertIn("use Node 20 or 22", text)

    def test_release_gate_workflow_frontend_e2e_summary_classifies_browser_network_failure(self) -> None:
        workflow_text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        summary_script_text = E2E_SUMMARY_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Frontend e2e summary", workflow_text)
        self.assertIn("node scripts/summarize-e2e-result.mjs", workflow_text)
        self.assertIn('--summary-title "Frontend e2e smoke"', workflow_text)
        self.assertIn('--markdown-summary-path "${GITHUB_STEP_SUMMARY:-}"', workflow_text)
        self.assertIn("getaddrinfo ENOTFOUND cdn.playwright.dev", summary_script_text)
        self.assertIn("browser_download_network", summary_script_text)

    def test_release_gate_workflow_uploads_frontend_e2e_summary_artifact(self) -> None:
        text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Upload frontend e2e summary artifact", text)
        self.assertIn("name: frontend-e2e-summary", text)
        self.assertIn("path: /tmp/frontend-e2e-summary.json", text)

    def test_release_gate_workflow_enforces_frontend_e2e_summary_schema(self) -> None:
        workflow_text = RELEASE_GATE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Frontend e2e summary schema gate", workflow_text)
        self.assertIn("node scripts/check-e2e-summary-schema.mjs", workflow_text)
        self.assertIn("--summary-path /tmp/frontend-e2e-summary.json", workflow_text)
        self.assertIn("--required-schema-version v1", workflow_text)
        schema_gate_text = E2E_SUMMARY_SCHEMA_GATE_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("REQUIRED_KEYS", schema_gate_text)
        self.assertIn("ALLOWED_RESULTS", schema_gate_text)
        self.assertIn("ALLOWED_CLASSIFICATIONS", schema_gate_text)
        self.assertIn("schema_version mismatch", schema_gate_text)


if __name__ == "__main__":
    unittest.main()
