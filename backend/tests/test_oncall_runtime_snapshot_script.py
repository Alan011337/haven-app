from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_oncall_runtime_snapshot.py"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

_SPEC = importlib.util.spec_from_file_location("run_oncall_runtime_snapshot", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class OncallRuntimeSnapshotScriptTests(unittest.TestCase):
    def test_main_writes_snapshot_from_local_payload_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            health_path = Path(tmp_dir) / "health.json"
            slo_path = Path(tmp_dir) / "health-slo.json"
            out_path = Path(tmp_dir) / "snapshot.json"
            health_path.write_text(
                json.dumps(
                    {
                        "status": "degraded",
                        "degraded_reasons": ["ai_router_burn_rate_above_threshold"],
                        "checks": {
                            "database": {"status": "ok"},
                            "redis": {"status": "ok"},
                            "notification_outbox_depth": 18,
                            "notification_outbox_retry_age_p95_seconds": 34,
                            "dynamic_content_fallback_ratio": 0.25,
                        },
                    }
                ),
                encoding="utf-8",
            )
            slo_path.write_text(
                json.dumps(
                    {
                        "sli": {
                            "evaluation": {
                                "ws": {"status": "ok"},
                                "ws_burn_rate": {"status": "ok"},
                                "ai_router_burn_rate": {"status": "degraded"},
                                "push": {"status": "insufficient_data"},
                                "cuj": {"status": "ok"},
                            },
                            "abuse_economics": {"evaluation": {"status": "ok"}},
                            "events_runtime": {
                                "ingest_guard": {
                                    "configured_backend": "redis",
                                    "active_backend": "memory",
                                    "redis_degraded_mode": True,
                                }
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            rc = _MODULE.main(
                [
                    "--health-file",
                    str(health_path),
                    "--health-slo-file",
                    str(slo_path),
                    "--output",
                    str(out_path),
                ]
            )
            self.assertEqual(rc, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("artifact_kind"), "oncall-runtime-snapshot")
            summary = payload.get("summary") or {}
            self.assertEqual(summary.get("health_status"), "degraded")
            self.assertEqual(summary.get("slo_ai_router_burn_rate_status"), "degraded")
            self.assertEqual(summary.get("events_ingest_guard_state", {}).get("active_backend"), "memory")


if __name__ == "__main__":
    unittest.main()
