from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
pytestmark = [pytest.mark.contract, pytest.mark.slow]


class OptimizationScriptsContractTests(unittest.TestCase):
    def _run(
        self,
        *args: str,
        timeout_seconds: float = 45.0,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.setdefault("DATABASE_URL", "sqlite:////tmp/haven-optimization-scripts-contract.db")
        if extra_env:
            env.update(extra_env)
        try:
            return subprocess.run(
                [sys.executable, *args],
                cwd=str(BACKEND_ROOT),
                text=True,
                capture_output=True,
                check=False,
                env=env,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(
                args=[sys.executable, *args],
                returncode=124,
                stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                stderr=f"timeout after {timeout_seconds}s",
            )

    def test_api_contract_sot_script_passes_with_repo_inventory(self) -> None:
        summary = Path(tempfile.gettempdir()) / "api-contract-sot-summary-test.json"
        proc = self._run(
            "scripts/check_api_contract_sot.py",
            "--inventory",
            str(ROOT / "docs/security/api-inventory.json"),
            "--summary-path",
            str(summary),
            "--require-api-prefix",
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        payload = json.loads(summary.read_text(encoding="utf-8"))
        self.assertEqual(payload["result"], "pass")

    def test_write_idempotency_script_passes_with_repo_inventory(self) -> None:
        summary = Path(tempfile.gettempdir()) / "idempotency-coverage-summary-test.json"
        proc = self._run(
            "scripts/check_write_idempotency_coverage.py",
            "--inventory",
            str(ROOT / "docs/security/api-inventory.json"),
            "--summary-path",
            str(summary),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        payload = json.loads(summary.read_text(encoding="utf-8"))
        self.assertEqual(payload["result"], "pass")
        self.assertGreaterEqual(payload["meta"]["mutating_api_total"], payload["meta"]["covered_total"])

    def test_outbox_slo_gate_flags_degraded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            snapshot = Path(td) / "outbox.json"
            summary = Path(td) / "summary.json"
            snapshot.write_text(
                json.dumps(
                    {
                        "outbox": {
                            "depth": 999,
                            "dead_letter_rate": 0.9,
                        }
                    }
                ),
                encoding="utf-8",
            )
            proc = self._run(
                "scripts/check_outbox_slo_gate.py",
                "--snapshot",
                str(snapshot),
                "--summary-path",
                str(summary),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "degraded")
            self.assertIn("outbox_depth_above_warn_threshold", payload["reasons"])

    def test_ai_runtime_gate_allows_degraded_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            snapshot = Path(td) / "ai.json"
            summary = Path(td) / "summary.json"
            snapshot.write_text(
                json.dumps(
                    {
                        "evaluation_result": "degraded",
                        "degraded_reasons": ["drift_detected"],
                    }
                ),
                encoding="utf-8",
            )
            proc = self._run(
                "scripts/check_ai_runtime_gate.py",
                "--snapshot",
                str(snapshot),
                "--allow-degraded",
                "--summary-path",
                str(summary),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "pass")

    def test_release_gate_wires_all_new_optimization_checks(self) -> None:
        script = (ROOT / "scripts/release-gate-local.sh").read_text(encoding="utf-8")
        required_tokens = [
            "check-worktree-materialization.py",
            "run_openapi_inventory_snapshot.py",
            "check_api_contract_sot.py",
            "check_write_idempotency_coverage.py",
            "check_idempotency_contract_convergence.py",
            "check_api_contract_snapshot.py",
            "check_outbox_slo_gate.py",
            "check_bola_coverage_from_inventory.py",
            "check_rate_limit_policy_contract.py",
            "check_ai_runtime_gate.py",
            "run_ai_router_runtime_persist.py",
            "check_timeline_perf_baseline_gate.py",
            "run_notification_outbox_self_heal.py",
            "run_data_retention_bundle.py",
            "RELEASE_GATE_STRICT_MODE",
            "RELEASE_GATE_ALLOW_SKIP_E2E_STRICT",
            "RELEASE_GATE_RUN_TIMELINE_PERF",
            "RELEASE_GATE_OUTBOX_FAIL_ON_DEGRADED",
            "OUTBOX_SELF_HEAL_POLICY_PATH",
            "run_full_pytest_stability_snapshot.py",
            "summarize_release_gate_noise.py",
            "check_observability_payload_contract.py",
            "run_data_rights_fire_drill_snapshot.py",
            "run_growth_cost_snapshot.py",
            "Frontend e2e smoke (skipped)",
            "--exit-code \"nan\"",
            "--degrade-timeout-in-dry-run",
            "api_contract,${API_CONTRACT_SOT_SUMMARY_PATH",
            "idempotency_coverage,${IDEMPOTENCY_COVERAGE_SUMMARY_PATH",
            "idempotency_convergence,${IDEMPOTENCY_CONVERGENCE_SUMMARY_PATH",
            "api_contract_snapshot,${API_CONTRACT_SNAPSHOT_SUMMARY_PATH",
            "bola_coverage,${BOLA_COVERAGE_SUMMARY_PATH",
            "rate_limit_policy,${RATE_LIMIT_POLICY_SUMMARY_PATH",
            "ai_runtime,${AI_RUNTIME_SUMMARY_PATH",
            "ai_router_multinode_stress,${AI_ROUTER_MULTINODE_STRESS_SUMMARY_PATH",
            "ai_router_runtime_persist,${AI_ROUTER_RUNTIME_PERSIST_SUMMARY_PATH",
            "timeline_perf,${TIMELINE_PERF_SUMMARY_PATH",
            "outbox_self_heal,${OUTBOX_SELF_HEAL_SUMMARY_PATH",
            "observability_contract,${OBSERVABILITY_CONTRACT_SUMMARY_PATH",
            "data_rights_drill,${DATA_RIGHTS_FIRE_DRILL_OUTPUT",
            "data_retention_bundle,${DATA_RETENTION_BUNDLE_SUMMARY_PATH",
            "growth_cost,${GROWTH_COST_SNAPSHOT_PATH",
            "full_pytest_stability,${FULL_PYTEST_STABILITY_SUMMARY_PATH",
            "worktree_materialization,${WORKTREE_MATERIALIZATION_SUMMARY_PATH",
            "npm run contract:types:check",
        ]
        for token in required_tokens:
            self.assertIn(token, script)

    def test_release_gate_local_orchestrator_wrapper_supports_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            summary = Path(td) / "orchestrator.json"
            stub_gate = Path(td) / "stub-release-gate.sh"
            stub_gate.write_text("#!/usr/bin/env bash\nset -euo pipefail\necho stub-release-gate\n", encoding="utf-8")
            stub_gate.chmod(0o755)
            proc = self._run(
                "scripts/run_release_gate_local_orchestrator.py",
                "--summary-path",
                str(summary),
                "--strict",
                "--allow-e2e-skip",
                "--release-gate-command",
                f"bash {stub_gate}",
                timeout_seconds=20.0,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            self.assertTrue(summary.exists(), msg=proc.stderr or proc.stdout)
            payload = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_kind"], "release-gate-local-orchestrator")
            self.assertEqual(payload["schema_version"], "v1")
            self.assertEqual(payload["result"], "pass")

    def test_worktree_materialization_script_passes_with_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            file_path = root / "sample.txt"
            summary = root / "summary.json"
            file_path.write_text("ok\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts/check-worktree-materialization.py"), "--root", str(root), "--summary-path", str(summary), "sample.txt"],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "pass")

    def test_worktree_materialization_can_degrade_with_allow_dataless(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            summary = root / "summary.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/check-worktree-materialization.py"),
                    "--root",
                    str(root),
                    "--allow-dataless",
                    "--summary-path",
                    str(summary),
                    "missing.txt",
                ],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "degraded")
            self.assertIn("missing_files", payload.get("reasons", []))

    def test_observability_payload_contract_passes_with_minimal_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            payload_path = Path(td) / "health-slo.json"
            summary = Path(td) / "summary.json"
            payload_path.write_text(
                json.dumps(
                    {
                        "sli": {
                            "notification_runtime": {"status": "ok"},
                            "dynamic_content_runtime": {"status": "ok"},
                        },
                        "checks": {"notification_outbox_depth": {"status": "ok"}},
                    }
                ),
                encoding="utf-8",
            )
            proc = self._run(
                "scripts/check_observability_payload_contract.py",
                "--payload-file",
                str(payload_path),
                "--summary-path",
                str(summary),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            self.assertEqual(json.loads(summary.read_text(encoding="utf-8"))["result"], "pass")

    def test_observability_payload_contract_can_skip_missing_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            payload_path = Path(td) / "health-slo.json"
            summary = Path(td) / "summary.json"
            payload_path.write_text(json.dumps({"sli": {}, "checks": {}}), encoding="utf-8")
            proc = self._run(
                "scripts/check_observability_payload_contract.py",
                "--payload-file",
                str(payload_path),
                "--allow-missing-keys",
                "--summary-path",
                str(summary),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            self.assertEqual(json.loads(summary.read_text(encoding="utf-8"))["result"], "skipped")

    def test_bola_coverage_inventory_gate_passes(self) -> None:
        summary = Path(tempfile.gettempdir()) / "bola-coverage-summary-test.json"
        proc = self._run(
            "scripts/check_bola_coverage_from_inventory.py",
            "--inventory",
            str(ROOT / "docs/security/api-inventory.json"),
            "--summary-path",
            str(summary),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        payload = json.loads(summary.read_text(encoding="utf-8"))
        self.assertEqual(payload["result"], "pass")

    def test_rate_limit_policy_contract_passes(self) -> None:
        summary = Path(tempfile.gettempdir()) / "rate-limit-policy-summary-test.json"
        proc = self._run(
            "scripts/check_rate_limit_policy_contract.py",
            "--source",
            str(ROOT / "backend/app/services/rate_limit_scope.py"),
            "--summary-path",
            str(summary),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        payload = json.loads(summary.read_text(encoding="utf-8"))
        self.assertEqual(payload["result"], "pass")

    def test_data_rights_and_growth_cost_snapshots_generate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fire_drill_json = Path(td) / "data-rights.json"
            fire_drill_md = Path(td) / "data-rights.md"
            growth_cost_json = Path(td) / "growth-cost.json"
            core_loop_summary = Path(td) / "core-loop-summary.json"
            outbox_summary = Path(td) / "outbox-summary.json"
            core_loop_summary.write_text(
                json.dumps({"result": "pass", "meta": {"evaluation_status": "pass"}}),
                encoding="utf-8",
            )
            outbox_summary.write_text(
                json.dumps({"result": "pass", "meta": {"depth": 0, "dead_letter_rate": 0.0}}),
                encoding="utf-8",
            )

            fire_drill_proc = self._run(
                "scripts/run_data_rights_fire_drill_snapshot.py",
                "--output",
                str(fire_drill_json),
                "--md-output",
                str(fire_drill_md),
                "--result",
                "pass",
            )
            self.assertEqual(fire_drill_proc.returncode, 0, msg=fire_drill_proc.stderr or fire_drill_proc.stdout)
            self.assertTrue(fire_drill_json.exists())
            self.assertTrue(fire_drill_md.exists())

            growth_proc = self._run(
                "scripts/run_growth_cost_snapshot.py",
                "--output",
                str(growth_cost_json),
                "--core-loop-summary",
                str(core_loop_summary),
                "--outbox-summary",
                str(outbox_summary),
                "--active-couples",
                "10",
                "--ai-cost-usd",
                "2",
                "--push-cost-usd",
                "1",
                "--db-cost-usd",
                "1",
                "--ws-cost-usd",
                "1",
            )
            self.assertEqual(growth_proc.returncode, 0, msg=growth_proc.stderr or growth_proc.stdout)
            payload = json.loads(growth_cost_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["cost"]["total_cost_usd"], 5.0)
            self.assertEqual(payload["cost"]["per_active_couple_cost_usd"], 0.5)

    def test_frontend_api_contract_types_check_passes(self) -> None:
        proc = subprocess.run(
            ["node", str(ROOT / "frontend/scripts/generate-api-contract-types.mjs"), "--check"],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)

    def test_full_pytest_stability_snapshot_supports_skip_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            summary = Path(td) / "summary.json"
            proc = self._run(
                "scripts/run_full_pytest_stability_snapshot.py",
                "--output",
                str(summary),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "skipped")

    def test_timeline_perf_gate_supports_allow_missing_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            summary = Path(td) / "summary.json"
            proc = self._run(
                "scripts/check_timeline_perf_baseline_gate.py",
                "--snapshot",
                str(Path(td) / "missing.json"),
                "--allow-missing-snapshot",
                "--summary-path",
                str(summary),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "skipped")

    def test_ai_router_runtime_persist_supports_missing_source_skip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "runtime.json"
            proc = self._run(
                "scripts/run_ai_router_runtime_persist.py",
                "--health-slo-file",
                str(Path(td) / "missing.json"),
                "--allow-missing-source",
                "--output",
                str(output),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "skipped")

    def test_ai_router_runtime_persist_prefers_file_source_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "runtime.json"
            payload_file = Path(td) / "health.json"
            payload_file.write_text(
                json.dumps(
                    {
                        "sli": {
                            "ai_router_runtime": {
                                "evaluation": {"result": "pass"},
                                "state": {"cooldown_active": False},
                                "counters": {"requests_total": 1},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            proc = self._run(
                "scripts/run_ai_router_runtime_persist.py",
                "--health-slo-file",
                str(payload_file),
                "--health-slo-url",
                "http://127.0.0.1:9/health/slo",
                "--output",
                str(output),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "pass")
            self.assertEqual(payload.get("meta", {}).get("source"), "file")

    def test_ai_router_runtime_persist_falls_back_to_url_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "runtime.json"
            payload_file = Path(td) / "health-slo-url.json"
            payload_file.write_text(
                json.dumps(
                    {
                        "sli": {
                            "ai_router_runtime": {
                                "evaluation": {"result": "pass"},
                                "state": {"cooldown_active": False},
                                "counters": {"requests_total": 2},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            proc = self._run(
                "scripts/run_ai_router_runtime_persist.py",
                "--health-slo-file",
                str(Path(td) / "missing.json"),
                "--health-slo-url",
                payload_file.resolve().as_uri(),
                "--output",
                str(output),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "pass")
            self.assertEqual(payload.get("meta", {}).get("source"), "url")

    def test_release_gate_noise_summary_supports_missing_orchestration(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "noise.json"
            proc = self._run(
                "scripts/summarize_release_gate_noise.py",
                "--orchestration-summary",
                str(Path(td) / "missing.json"),
                "--allow-missing-summary",
                "--output",
                str(output),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "skipped")

    def test_outbox_self_heal_supports_missing_snapshot_skip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "outbox-self-heal.json"
            proc = self._run(
                "scripts/run_notification_outbox_self_heal.py",
                "--snapshot",
                str(Path(td) / "missing.json"),
                "--allow-missing-snapshot",
                "--output",
                str(output),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "skipped")

    def test_outbox_self_heal_apply_safe_actions_still_skips_when_snapshot_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "outbox-self-heal-apply.json"
            proc = self._run(
                "scripts/run_notification_outbox_self_heal.py",
                "--snapshot",
                str(Path(td) / "missing.json"),
                "--allow-missing-snapshot",
                "--apply-safe-actions",
                "--output",
                str(output),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "skipped")
            self.assertEqual(payload.get("applied_actions") or [], [])

    def test_data_retention_bundle_dry_run_allows_job_failures(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "data-retention.json"
            proc = self._run(
                "scripts/run_data_retention_bundle.py",
                "--allow-job-failures",
                "--job-timeout-seconds",
                "5",
                "--output",
                str(output),
                timeout_seconds=40.0,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn(payload["result"], {"pass", "degraded"})

    def test_ai_router_multinode_stress_allows_empty_mode_list_for_contract_validation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "router-stress.json"
            proc = self._run(
                "scripts/run_ai_router_multinode_stress.py",
                "--modes",
                "",
                "--runs",
                "1",
                "--output",
                str(output),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "pass")
            self.assertEqual(payload["meta"]["total_executions"], 0)


if __name__ == "__main__":
    unittest.main()
