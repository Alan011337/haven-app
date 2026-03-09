import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import main as main_module  # noqa: E402
from app.core import health_routes as health_routes_module  # noqa: E402


class HealthEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main_module.app)

    def tearDown(self) -> None:
        self.client.close()

    def test_health_returns_ok_with_runtime_and_sli(self) -> None:
        sqlite_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(sqlite_engine.dispose)

        with patch.object(health_routes_module, "engine", sqlite_engine), patch.object(
            health_routes_module,
            "_probe_redis_if_configured",
            return_value={"status": "skipped", "reason": "backend_not_redis"},
        ), patch.object(
            health_routes_module,
            "_build_abuse_economics_sli_payload",
            return_value={
                "status": "ok",
                "evaluation": {"status": "ok", "reasons": [], "signal_present": False},
            },
        ):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("uptime_seconds", payload)
        self.assertEqual(payload["checks"]["database"]["status"], "ok")
        self.assertEqual(payload["checks"]["redis"]["status"], "skipped")
        self.assertIn("notification_outbox_oldest_pending_age_seconds", payload["checks"])
        self.assertIn("notification_outbox_stale_processing_count", payload["checks"])
        self.assertIn("notification_outbox_dispatch_lock_heartbeat_age_seconds", payload["checks"])
        self.assertIn("dynamic_content_fallback_ratio", payload["checks"])
        self.assertIn("db_query_runtime", payload["checks"])
        self.assertIn("sli", payload)
        self.assertIn("ws", payload["sli"])
        self.assertIn("ws_burn_rate", payload["sli"])
        self.assertIn("push", payload["sli"])
        self.assertIn("cuj", payload["sli"])
        self.assertIn("abuse_economics", payload["sli"])
        self.assertIn("evaluation", payload["sli"])
        self.assertIn("ws", payload["sli"]["evaluation"])
        self.assertIn("ws_burn_rate", payload["sli"]["evaluation"])
        self.assertIn("ai_router_burn_rate", payload["sli"]["evaluation"])
        self.assertIn("push", payload["sli"]["evaluation"])
        self.assertIn("cuj", payload["sli"]["evaluation"])
        self.assertIn("write_rate_limit", payload["sli"])
        self.assertIn("attempt_total", payload["sli"]["write_rate_limit"])
        self.assertIn("blocked_total", payload["sli"]["write_rate_limit"])
        self.assertIn("block_rate_overall", payload["sli"]["write_rate_limit"])
        self.assertIn("ai_router_runtime", payload["sli"])
        self.assertIn("notification_runtime", payload["sli"])
        self.assertIn("dynamic_content_runtime", payload["sli"])
        self.assertIn("events_runtime", payload["sli"])
        self.assertIn("timeline_runtime", payload["sli"])
        self.assertIn("ingest_guard", payload["sli"]["events_runtime"])
        self.assertIn("configured_backend", payload["sli"]["events_runtime"]["ingest_guard"])
        self.assertIn("active_backend", payload["sli"]["events_runtime"]["ingest_guard"])
        self.assertIn("redis_degraded_mode", payload["sli"]["events_runtime"]["ingest_guard"])
        self.assertIn("state", payload["sli"]["dynamic_content_runtime"])
        dynamic_state = payload["sli"]["dynamic_content_runtime"]["state"]
        self.assertIn("degraded_mode_active", dynamic_state)
        self.assertIn("degraded_mode_remaining_seconds", dynamic_state)
        self.assertIn("degraded_mode_recovery_threshold", dynamic_state)
        self.assertIn("degraded_mode_recovery_min_attempts", dynamic_state)
        self.assertIn("targets", payload["sli"])

    def test_health_returns_degraded_when_database_probe_fails(self) -> None:
        with patch.object(
            health_routes_module,
            "_probe_database",
            return_value={"status": "error", "latency_ms": 1.23, "error": "OperationalError"},
        ), patch.object(
            health_routes_module,
            "_probe_redis_if_configured",
            return_value={"status": "skipped", "reason": "backend_not_redis"},
        ):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "degraded")
        self.assertIn("database_unhealthy", payload["degraded_reasons"])

    def test_health_slo_endpoint_returns_targets(self) -> None:
        response = self.client.get("/health/slo")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("checks", payload)
        self.assertIn("notification_outbox_depth", payload["checks"])
        self.assertIn("dynamic_content_fallback_ratio", payload["checks"])
        self.assertIn("sli", payload)
        self.assertIn("ws", payload["sli"])
        self.assertIn("ws_burn_rate", payload["sli"])
        self.assertIn("push", payload["sli"])
        self.assertIn("cuj", payload["sli"])
        self.assertIn("abuse_economics", payload["sli"])
        self.assertIn("evaluation", payload["sli"])
        self.assertIn("ws", payload["sli"]["evaluation"])
        self.assertIn("ws_burn_rate", payload["sli"]["evaluation"])
        self.assertIn("ai_router_burn_rate", payload["sli"]["evaluation"])
        self.assertIn("push", payload["sli"]["evaluation"])
        self.assertIn("cuj", payload["sli"]["evaluation"])
        self.assertIn("write_rate_limit", payload["sli"])
        self.assertIn("attempt_total", payload["sli"]["write_rate_limit"])
        self.assertIn("blocked_total", payload["sli"]["write_rate_limit"])
        self.assertIn("block_rate_overall", payload["sli"]["write_rate_limit"])
        self.assertIn("ai_router_runtime", payload["sli"])
        self.assertIn("notification_runtime", payload["sli"])
        self.assertIn("dynamic_content_runtime", payload["sli"])
        self.assertIn("events_runtime", payload["sli"])
        self.assertIn("timeline_runtime", payload["sli"])
        self.assertIn("ingest_guard", payload["sli"]["events_runtime"])
        self.assertIn("configured_backend", payload["sli"]["events_runtime"]["ingest_guard"])
        self.assertIn("active_backend", payload["sli"]["events_runtime"]["ingest_guard"])
        self.assertIn("redis_degraded_mode", payload["sli"]["events_runtime"]["ingest_guard"])
        self.assertIn("state", payload["sli"]["dynamic_content_runtime"])
        dynamic_state = payload["sli"]["dynamic_content_runtime"]["state"]
        self.assertIn("degraded_mode_active", dynamic_state)
        self.assertIn("degraded_mode_remaining_seconds", dynamic_state)
        self.assertIn("degraded_mode_recovery_threshold", dynamic_state)
        self.assertIn("degraded_mode_recovery_min_attempts", dynamic_state)
        self.assertEqual(payload["sli"]["targets"]["ws_connection_accept_rate"], 0.995)
        self.assertEqual(payload["sli"]["targets"]["ws_message_pass_rate"], 0.99)
        self.assertEqual(payload["sli"]["targets"]["ws_burn_rate_fast_threshold"], 14.4)
        self.assertEqual(payload["sli"]["targets"]["ws_burn_rate_slow_threshold"], 6.0)
        self.assertIn("ai_router_burn_rate_fast_window_seconds", payload["sli"]["targets"])
        self.assertIn("ai_router_burn_rate_slow_window_seconds", payload["sli"]["targets"])
        self.assertIn("ai_router_burn_rate_fast_threshold", payload["sli"]["targets"])
        self.assertIn("ai_router_burn_rate_slow_threshold", payload["sli"]["targets"])
        self.assertIn("push_delivery_rate", payload["sli"]["targets"])
        self.assertIn("push_dispatch_latency_p95_ms", payload["sli"]["targets"])
        self.assertIn("push_dry_run_latency_p95_ms", payload["sli"]["targets"])
        self.assertIn("push_cleanup_stale_backlog_max", payload["sli"]["targets"])
        self.assertIn("cuj", payload["sli"]["targets"])
        cuj = payload["sli"].get("cuj") or {}
        if cuj.get("status") == "ok":
            self.assertIn("metrics", cuj, msg="SLO-01: GET /health/slo cuj snapshot must expose metrics when status=ok")
            self.assertIn("ritual_success_rate", cuj.get("metrics") or {}, msg="SLO-01: ritual_success_rate must be in cuj.metrics")

    def test_metrics_endpoint_returns_openmetrics_payload(self) -> None:
        with patch.object(
            health_routes_module.notification_runtime_metrics,
            "snapshot",
            return_value={"notification_attempt_in_app_ws_total": 2, "notification_success_in_app_ws_total": 1},
        ), patch.object(
            health_routes_module.dynamic_content_runtime_metrics,
            "snapshot",
            return_value={"dynamic_content_success_total": 3},
        ), patch.object(
            health_routes_module.events_runtime_metrics,
            "snapshot",
            return_value={"events_ingest_attempt_total": 5},
        ), patch.object(
            health_routes_module.timeline_runtime_metrics,
            "snapshot",
            return_value={"timeline_query_total": 7},
        ), patch.object(
            health_routes_module,
            "get_notification_outbox_depth",
            return_value=4,
        ), patch.object(
            health_routes_module,
            "get_notification_outbox_oldest_pending_age_seconds",
            return_value=12,
        ), patch.object(
            health_routes_module,
            "get_notification_outbox_stale_processing_count",
            return_value=3,
        ):
            response = self.client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        content_type = response.headers.get("content-type", "")
        self.assertIn("text/plain", content_type)
        body = response.text
        self.assertIn("haven_service_info", body)
        self.assertIn("haven_notification_outbox_depth 4", body)
        self.assertIn("haven_notification_outbox_oldest_pending_age_seconds 12", body)
        self.assertIn("haven_notification_outbox_stale_processing_count 3", body)
        self.assertIn("haven_notification_runtime_notification_attempt_in_app_ws_total 2", body)
        self.assertIn("haven_dynamic_content_runtime_dynamic_content_success_total 3", body)
        self.assertIn("haven_events_runtime_events_ingest_attempt_total 5", body)
        self.assertIn("haven_timeline_runtime_timeline_query_total 7", body)

    def test_health_deep_alias_returns_sli_snapshot(self) -> None:
        response = self.client.get("/health/deep")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("status"), "ok")
        self.assertIn("sli", payload)

    def test_metrics_endpoint_rejects_missing_token_when_auth_required(self) -> None:
        with patch.object(health_routes_module.settings, "METRICS_REQUIRE_AUTH", True), patch.object(
            health_routes_module.settings, "METRICS_AUTH_TOKEN", "metrics-secret"
        ):
            response = self.client.get("/metrics")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json().get("detail"), "Metrics authentication failed.")

    def test_metrics_endpoint_accepts_valid_token_when_auth_required(self) -> None:
        with patch.object(health_routes_module.settings, "METRICS_REQUIRE_AUTH", True), patch.object(
            health_routes_module.settings, "METRICS_AUTH_TOKEN", "metrics-secret"
        ):
            response = self.client.get(
                "/metrics",
                headers={"X-Metrics-Token": "metrics-secret"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("haven_service_info", response.text)

    def test_health_slo_cuj_metrics_include_ritual_success_rate_slo01(self) -> None:
        """SLO-01: Contract test — when cuj snapshot is ok, metrics must include ritual_success_rate (backend+frontend CUJ aggregation)."""
        cuj_snapshot = {
            "status": "ok",
            "window_hours": 24,
            "counts": {"ritual_draw_total": 100, "ritual_unlock_total": 99},
            "metrics": {"ritual_success_rate": 0.99, "partner_binding_success_rate": 1.0},
            "samples": {"journal_write_latency_samples": 50, "analysis_async_lag_samples": 50},
            "targets": {},
        }
        with patch.object(health_routes_module, "_build_cuj_sli_payload", return_value=cuj_snapshot):
            response = self.client.get("/health/slo")
        self.assertEqual(response.status_code, 200)
        sli_cuj = response.json().get("sli", {}).get("cuj", {})
        self.assertEqual(sli_cuj.get("status"), "ok")
        self.assertIn("ritual_success_rate", sli_cuj.get("metrics") or {})

    def test_health_returns_degraded_when_ws_sli_below_target(self) -> None:
        ws_sli_payload = {
            "connection_attempts_total": 200,
            "connections_accepted_total": 160,
            "connections_rejected_total": 40,
            "connection_accept_rate": 0.8,
            "messages_received_total": 500,
            "messages_blocked_total": 20,
            "messages_passed_total": 480,
            "message_pass_rate": 0.96,
        }

        with patch.object(
            health_routes_module,
            "_probe_database",
            return_value={"status": "ok", "latency_ms": 1.0},
        ), patch.object(
            health_routes_module,
            "_probe_redis_if_configured",
            return_value={"status": "skipped", "reason": "backend_not_redis"},
        ), patch.object(
            health_routes_module,
            "_build_ws_sli_payload",
            return_value=ws_sli_payload,
        ), patch.object(
            health_routes_module,
            "_build_cuj_sli_payload",
            return_value={"status": "insufficient_data"},
        ):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "degraded")
        self.assertIn("ws_sli_below_target", payload["degraded_reasons"])
        ws_eval = payload["sli"]["evaluation"]["ws"]
        self.assertEqual(ws_eval["status"], "degraded")
        self.assertIn("ws_connection_accept_rate_below_target", ws_eval["reasons"])
        self.assertIn("ws_message_pass_rate_below_target", ws_eval["reasons"])

    def test_health_returns_degraded_when_outbox_depth_crosses_threshold(self) -> None:
        with patch.object(
            health_routes_module,
            "_probe_database",
            return_value={"status": "ok", "latency_ms": 1.0},
        ), patch.object(
            health_routes_module,
            "_probe_redis_if_configured",
            return_value={"status": "skipped", "reason": "backend_not_redis"},
        ), patch.object(
            health_routes_module,
            "get_notification_outbox_depth",
            return_value=max(1, health_routes_module.HEALTH_OUTBOX_DEPTH_DEGRADED_THRESHOLD),
        ):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertIn("notification_outbox_depth_high", payload.get("degraded_reasons", []))

    def test_health_returns_degraded_when_outbox_retry_age_crosses_threshold(self) -> None:
        with patch.object(
            health_routes_module,
            "_probe_database",
            return_value={"status": "ok", "latency_ms": 1.0},
        ), patch.object(
            health_routes_module,
            "_probe_redis_if_configured",
            return_value={"status": "skipped", "reason": "backend_not_redis"},
        ), patch.object(
            health_routes_module,
            "get_notification_outbox_retry_age_p95_seconds",
            return_value=max(
                1,
                health_routes_module.HEALTH_OUTBOX_RETRY_AGE_P95_DEGRADED_SECONDS,
            ),
        ):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertIn("notification_outbox_retry_age_high", payload.get("degraded_reasons", []))

    def test_health_returns_degraded_when_ws_burn_rate_above_threshold(self) -> None:
        ws_sli_payload = {
            "connection_attempts_total": 200,
            "connections_accepted_total": 199,
            "connections_rejected_total": 1,
            "connection_accept_rate": 0.995,
            "messages_received_total": 500,
            "messages_blocked_total": 5,
            "messages_passed_total": 495,
            "message_pass_rate": 0.99,
        }
        ws_burn_rate_payload = {
            "windows": [
                {
                    "window_seconds": 300,
                    "connection_burn_rate": 20.0,
                    "enough_connection_samples": True,
                    "message_burn_rate": 1.0,
                    "enough_message_samples": True,
                },
                {
                    "window_seconds": 3600,
                    "connection_burn_rate": 16.0,
                    "enough_connection_samples": True,
                    "message_burn_rate": 1.0,
                    "enough_message_samples": True,
                },
                {
                    "window_seconds": 21600,
                    "connection_burn_rate": 1.0,
                    "enough_connection_samples": True,
                    "message_burn_rate": 1.0,
                    "enough_message_samples": True,
                },
                {
                    "window_seconds": 86400,
                    "connection_burn_rate": 1.0,
                    "enough_connection_samples": True,
                    "message_burn_rate": 1.0,
                    "enough_message_samples": True,
                },
            ]
        }

        with patch.object(
            health_routes_module,
            "_probe_database",
            return_value={"status": "ok", "latency_ms": 1.0},
        ), patch.object(
            health_routes_module,
            "_probe_redis_if_configured",
            return_value={"status": "skipped", "reason": "backend_not_redis"},
        ), patch.object(
            health_routes_module,
            "_build_ws_sli_payload",
            return_value=ws_sli_payload,
        ), patch.object(
            health_routes_module,
            "_build_ws_burn_rate_payload",
            return_value=ws_burn_rate_payload,
        ), patch.object(
            health_routes_module,
            "_build_cuj_sli_payload",
            return_value={"status": "insufficient_data"},
        ):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "degraded")
        self.assertIn("ws_burn_rate_above_threshold", payload["degraded_reasons"])
        ws_burn_eval = payload["sli"]["evaluation"]["ws_burn_rate"]
        self.assertEqual(ws_burn_eval["status"], "degraded")
        self.assertIn(
            "ws_connection_burn_rate_fast_windows_above_threshold",
            ws_burn_eval["reasons"],
        )

    def test_health_returns_degraded_when_ai_router_burn_rate_above_threshold(self) -> None:
        with patch.object(
            health_routes_module,
            "_probe_database",
            return_value={"status": "ok", "latency_ms": 1.0},
        ), patch.object(
            health_routes_module,
            "_probe_redis_if_configured",
            return_value={"status": "skipped", "reason": "backend_not_redis"},
        ), patch.object(
            health_routes_module,
            "_build_ai_router_runtime_payload",
            return_value={
                "counters": {},
                "state": {},
                "burn_rate": {
                    "status": "degraded",
                    "reasons": [
                        "ai_router_burn_rate_fast_exceeded",
                        "ai_router_burn_rate_slow_exceeded",
                    ],
                    "error_budget_fraction": 0.01,
                    "fast_window": {
                        "window_seconds": 300,
                        "attempts_total": 100,
                        "failures_total": 20,
                        "failure_rate": 0.2,
                        "burn_rate": 20.0,
                        "threshold": 14.4,
                        "min_attempts": 20,
                        "enough_samples": True,
                    },
                    "slow_window": {
                        "window_seconds": 3600,
                        "attempts_total": 200,
                        "failures_total": 18,
                        "failure_rate": 0.09,
                        "burn_rate": 9.0,
                        "threshold": 6.0,
                        "min_attempts": 100,
                        "enough_samples": True,
                    },
                },
            },
        ):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "degraded")
        self.assertIn("ai_router_burn_rate_above_threshold", payload["degraded_reasons"])
        ai_router_eval = payload["sli"]["evaluation"]["ai_router_burn_rate"]
        self.assertEqual(ai_router_eval["status"], "degraded")
        self.assertIn("ai_router_burn_rate_fast_window_exceeded", ai_router_eval["reasons"])
        self.assertIn("ai_router_burn_rate_slow_window_exceeded", ai_router_eval["reasons"])

    def test_health_returns_degraded_when_cuj_sli_below_target(self) -> None:
        with patch.object(
            health_routes_module,
            "_probe_database",
            return_value={"status": "ok", "latency_ms": 1.0},
        ), patch.object(
            health_routes_module,
            "_probe_redis_if_configured",
            return_value={"status": "skipped", "reason": "backend_not_redis"},
        ), patch.object(
            health_routes_module,
            "_evaluate_cuj_sli",
            return_value={
                "status": "degraded",
                "reasons": ["ritual_success_rate_below_target"],
                "evaluated": {},
            },
        ):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "degraded")
        self.assertIn("cuj_sli_below_target", payload["degraded_reasons"])
        cuj_eval = payload["sli"]["evaluation"]["cuj"]
        self.assertEqual(cuj_eval["status"], "degraded")
        self.assertIn("ritual_success_rate_below_target", cuj_eval["reasons"])

    def test_health_degradation_endpoint_returns_ok_when_healthy(self) -> None:
        """DEG-01: Explicit degradation API returns ok when no features degraded."""
        with patch.object(
            health_routes_module,
            "evaluate_degradation_status",
            return_value={"status": "ok", "features": {}},
        ):
            response = self.client.get("/health/degradation")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["features"], {})
        self.assertIn("timestamp", payload)

    def test_health_degradation_endpoint_returns_features_when_degraded(self) -> None:
        """DEG-01: Explicit degradation API returns per-feature fallback copy for frontend."""
        with patch.object(
            health_routes_module,
            "evaluate_degradation_status",
            return_value={
                "status": "degraded",
                "features": {
                    "journal_write": {
                        "fallback": "Journal will be saved locally and synced when service recovers.",
                        "severity": "warning",
                    },
                },
            },
        ):
            response = self.client.get("/health/degradation")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "degraded")
        self.assertIn("journal_write", payload["features"])
        self.assertEqual(
            payload["features"]["journal_write"]["fallback"],
            "Journal will be saved locally and synced when service recovers.",
        )
        self.assertEqual(payload["features"]["journal_write"]["severity"], "warning")

    def test_health_returns_degraded_when_abuse_economics_blocked(self) -> None:
        with patch.object(
            health_routes_module,
            "_probe_database",
            return_value={"status": "ok", "latency_ms": 1.0},
        ), patch.object(
            health_routes_module,
            "_probe_redis_if_configured",
            return_value={"status": "skipped", "reason": "backend_not_redis"},
        ), patch.object(
            health_routes_module,
            "_build_abuse_economics_sli_payload",
            return_value={
                "status": "block",
                "evaluation": {
                    "status": "block",
                    "reasons": ["daily_total_cost_above_block_threshold"],
                    "signal_present": True,
                },
            },
        ):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "degraded")
        self.assertIn("abuse_economics_budget_block", payload["degraded_reasons"])


if __name__ == "__main__":
    unittest.main()
