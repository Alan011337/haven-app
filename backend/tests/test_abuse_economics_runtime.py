import json
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.abuse_economics_runtime import (  # noqa: E402
    build_abuse_economics_runtime_snapshot,
)


def _minimal_policy_payload() -> dict:
    return {
        "artifact_kind": "abuse-economics-policy",
        "schema_version": "1.0.0",
        "vectors": [
            {
                "id": "signup_abuse",
                "description": "signup abuse",
                "unit_cost_usd": 0.1,
                "max_events_per_user_per_day": 10,
                "max_events_per_ip_per_day": 20,
                "mapped_controls": ["backend/app/api/login.py"],
            },
            {
                "id": "pairing_bruteforce",
                "description": "pairing abuse",
                "unit_cost_usd": 0.01,
                "max_events_per_user_per_day": 100,
                "max_events_per_ip_per_day": 200,
                "mapped_controls": ["backend/app/services/pairing_abuse_guard.py"],
            },
            {
                "id": "ws_storm",
                "description": "ws abuse",
                "unit_cost_usd": 0.001,
                "max_events_per_user_per_day": 1000,
                "max_events_per_ip_per_day": 2000,
                "mapped_controls": ["backend/app/services/ws_abuse_guard.py"],
            },
        ],
        "escalation_thresholds": {
            "warn_daily_total_usd": 5.0,
            "block_daily_total_usd": 10.0,
        },
    }


class AbuseEconomicsRuntimeTests(unittest.TestCase):
    def test_missing_policy_returns_insufficient_data(self) -> None:
        payload = build_abuse_economics_runtime_snapshot(
            rate_limit_snapshot={},
            ws_runtime_snapshot={},
            uptime_seconds=120,
            policy_path=Path("/tmp/this-policy-does-not-exist.json"),
        )
        self.assertEqual(payload["status"], "insufficient_data")
        self.assertEqual(payload["evaluation"]["status"], "insufficient_data")

    def test_block_when_estimated_daily_cost_exceeds_block_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_path = Path(tmp_dir) / "abuse-policy.json"
            policy_path.write_text(
                json.dumps(_minimal_policy_payload()),
                encoding="utf-8",
            )
            payload = build_abuse_economics_runtime_snapshot(
                rate_limit_snapshot={
                    "blocked_by_action": {
                        "login": 5,
                    }
                },
                ws_runtime_snapshot={"counters": {}},
                uptime_seconds=60,
                policy_path=policy_path,
            )

        self.assertEqual(payload["status"], "block")
        self.assertEqual(payload["evaluation"]["status"], "block")
        self.assertIn("daily_total_cost_above_block_threshold", payload["evaluation"]["reasons"])

    def test_pairing_vector_uses_pairing_attempt_counter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_path = Path(tmp_dir) / "abuse-policy.json"
            policy_path.write_text(
                json.dumps(_minimal_policy_payload()),
                encoding="utf-8",
            )
            payload = build_abuse_economics_runtime_snapshot(
                rate_limit_snapshot={"blocked_by_action": {"pairing_attempt": 3}},
                ws_runtime_snapshot={"counters": {}},
                uptime_seconds=600,
                policy_path=policy_path,
            )

        vector = next(item for item in payload["vectors"] if item["id"] == "pairing_bruteforce")
        self.assertEqual(vector["observed_events_total"], 3)
        self.assertEqual(
            vector["signal_source"],
            "rate_limit.blocked_by_action.pairing_attempt",
        )

    def test_ws_vector_aggregates_rejection_and_block_counters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_path = Path(tmp_dir) / "abuse-policy.json"
            policy_path.write_text(
                json.dumps(_minimal_policy_payload()),
                encoding="utf-8",
            )
            payload = build_abuse_economics_runtime_snapshot(
                rate_limit_snapshot={},
                ws_runtime_snapshot={
                    "counters": {
                        "connections_rejected_invalid_token": 2,
                        "messages_rate_limited": 4,
                    }
                },
                uptime_seconds=600,
                policy_path=policy_path,
            )

        vector = next(item for item in payload["vectors"] if item["id"] == "ws_storm")
        self.assertEqual(vector["observed_events_total"], 6)


if __name__ == "__main__":
    unittest.main()
