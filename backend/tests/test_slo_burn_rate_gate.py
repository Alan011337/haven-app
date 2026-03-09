import importlib.util
import json
import ssl
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_slo_burn_rate_gate.py"
_SPEC = importlib.util.spec_from_file_location("check_slo_burn_rate_gate", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

evaluate_slo_payload = _MODULE.evaluate_slo_payload
main = _MODULE.main


def _ok_payload() -> dict:
    return {
        "sli": {
            "abuse_economics": {"evaluation": {"status": "ok"}},
            "evaluation": {
                "ws": {"status": "ok"},
                "ws_burn_rate": {"status": "ok"},
                "ai_router_burn_rate": {"status": "ok"},
                "push": {"status": "ok"},
                "cuj": {"status": "ok"},
            },
        }
    }


class SloBurnRateGateTests(unittest.TestCase):
    def test_evaluate_passes_when_ws_and_burn_rate_ok(self) -> None:
        passed, reasons, statuses = evaluate_slo_payload(_ok_payload())
        self.assertTrue(passed)
        self.assertEqual(reasons, [])
        self.assertEqual(statuses["ws"], "ok")
        self.assertEqual(statuses["ws_burn_rate"], "ok")
        self.assertEqual(statuses["ai_router_burn_rate"], "ok")
        self.assertEqual(statuses["push"], "ok")
        self.assertEqual(statuses["cuj"], "ok")
        self.assertEqual(statuses["abuse_economics"], "ok")

    def test_evaluate_fails_when_burn_rate_degraded(self) -> None:
        payload = _ok_payload()
        payload["sli"]["evaluation"]["ws_burn_rate"]["status"] = "degraded"
        passed, reasons, _statuses = evaluate_slo_payload(payload)
        self.assertFalse(passed)
        self.assertIn("ws_burn_rate_degraded", reasons)

    def test_evaluate_fails_when_ai_router_burn_rate_degraded(self) -> None:
        payload = _ok_payload()
        payload["sli"]["evaluation"]["ai_router_burn_rate"]["status"] = "degraded"
        passed, reasons, statuses = evaluate_slo_payload(payload)
        self.assertFalse(passed)
        self.assertIn("ai_router_burn_rate_degraded", reasons)
        self.assertEqual(statuses["ai_router_burn_rate"], "degraded")

    def test_evaluate_fails_when_cuj_degraded(self) -> None:
        payload = _ok_payload()
        payload["sli"]["evaluation"]["cuj"]["status"] = "degraded"
        passed, reasons, statuses = evaluate_slo_payload(payload)
        self.assertFalse(passed)
        self.assertIn("cuj_sli_degraded", reasons)
        self.assertEqual(statuses["cuj"], "degraded")

    def test_evaluate_fails_when_push_degraded(self) -> None:
        payload = _ok_payload()
        payload["sli"]["evaluation"]["push"]["status"] = "degraded"
        passed, reasons, statuses = evaluate_slo_payload(payload)
        self.assertFalse(passed)
        self.assertIn("push_sli_degraded", reasons)
        self.assertEqual(statuses["push"], "degraded")

    def test_evaluate_fails_when_abuse_economics_block(self) -> None:
        payload = _ok_payload()
        payload["sli"]["abuse_economics"]["evaluation"]["status"] = "block"
        passed, reasons, statuses = evaluate_slo_payload(payload)
        self.assertFalse(passed)
        self.assertIn("abuse_economics_block", reasons)
        self.assertEqual(statuses["abuse_economics"], "block")

    def test_evaluate_warn_does_not_fail_by_default(self) -> None:
        payload = _ok_payload()
        payload["sli"]["abuse_economics"]["evaluation"]["status"] = "warn"
        passed, reasons, statuses = evaluate_slo_payload(payload)
        self.assertTrue(passed)
        self.assertEqual(reasons, [])
        self.assertEqual(statuses["abuse_economics"], "warn")

    def test_evaluate_warn_can_fail_when_enabled(self) -> None:
        payload = _ok_payload()
        payload["sli"]["abuse_economics"]["evaluation"]["status"] = "warn"
        passed, reasons, _statuses = evaluate_slo_payload(payload, fail_on_abuse_warn=True)
        self.assertFalse(passed)
        self.assertIn("abuse_economics_warn", reasons)

    def test_evaluate_allows_missing_cuj_as_insufficient_data_during_rollout(self) -> None:
        payload = {
            "sli": {
                "abuse_economics": {"evaluation": {"status": "ok"}},
                "evaluation": {
                    "ws": {"status": "ok"},
                    "ws_burn_rate": {"status": "ok"},
                },
            }
        }
        passed, reasons, statuses = evaluate_slo_payload(payload)
        self.assertTrue(passed)
        self.assertEqual(reasons, [])
        self.assertEqual(statuses["push"], "insufficient_data")
        self.assertEqual(statuses["cuj"], "insufficient_data")
        self.assertEqual(statuses["ai_router_burn_rate"], "insufficient_data")
        self.assertEqual(statuses["abuse_economics"], "ok")

    def test_evaluate_can_require_sufficient_data(self) -> None:
        payload = {
            "sli": {
                "abuse_economics": {"evaluation": {"status": "insufficient_data"}},
                "evaluation": {
                    "ws": {"status": "insufficient_data"},
                    "ws_burn_rate": {"status": "insufficient_data"},
                    "ai_router_burn_rate": {"status": "insufficient_data"},
                    "push": {"status": "insufficient_data"},
                    "cuj": {"status": "insufficient_data"},
                },
            }
        }
        passed, reasons, _statuses = evaluate_slo_payload(
            payload,
            require_sufficient_data=True,
        )
        self.assertFalse(passed)
        self.assertIn("ws_sli_insufficient_data", reasons)
        self.assertIn("ws_burn_rate_insufficient_data", reasons)
        self.assertIn("ai_router_burn_rate_insufficient_data", reasons)
        self.assertIn("push_sli_insufficient_data", reasons)
        self.assertIn("cuj_sli_insufficient_data", reasons)
        self.assertIn("abuse_economics_insufficient_data", reasons)

    def test_fetch_payload_retries_with_certifi_context_on_ssl_verification_error(self) -> None:
        payload_text = json.dumps(_ok_payload())
        ssl_error = ssl.SSLCertVerificationError(
            1,
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)",
        )
        calls: list[object] = []

        class _FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return None

            def read(self) -> bytes:
                return payload_text.encode("utf-8")

            def getcode(self) -> int:
                return 200

        def _fake_urlopen(request_obj, timeout, context):  # type: ignore[no-untyped-def]
            calls.append(context)
            if len(calls) == 1:
                raise _MODULE.error.URLError(ssl_error)
            return _FakeResponse()

        with patch.object(_MODULE, "_iter_ssl_contexts", return_value=["default_ctx", "certifi_ctx"]), patch.object(
            _MODULE.request,
            "urlopen",
            side_effect=_fake_urlopen,
        ):
            payload = _MODULE._fetch_json_payload(
                url="https://example.com/health/slo",
                timeout_seconds=10.0,
                bearer_token=None,
            )

        self.assertEqual(payload["sli"]["evaluation"]["ws"]["status"], "ok")
        self.assertEqual(calls, ["default_ctx", "certifi_ctx"])

    def test_main_skips_when_allow_missing_url(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "SLO_GATE_HEALTH_SLO_URL": "",
                "SLO_GATE_HEALTH_SLO_FILE": "",
                "SLO_GATE_BEARER_TOKEN": "",
            },
            clear=False,
        ):
            exit_code = main(["--allow-missing-url"])
        self.assertEqual(exit_code, 0)

    def test_main_fails_when_fetch_payload_is_degraded(self) -> None:
        degraded_payload = _ok_payload()
        degraded_payload["sli"]["evaluation"]["ws_burn_rate"]["status"] = "degraded"
        with patch.object(_MODULE, "_fetch_json_payload", return_value=degraded_payload):
            exit_code = main(["--url", "https://example.com/health/slo"])
        self.assertEqual(exit_code, 1)

    def test_main_fails_when_missing_url_without_allow_flag(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "SLO_GATE_HEALTH_SLO_URL": "",
                "SLO_GATE_HEALTH_SLO_FILE": "",
                "SLO_GATE_BEARER_TOKEN": "",
            },
            clear=False,
        ):
            exit_code = main([])
        self.assertEqual(exit_code, 1)

    def test_main_fails_when_require_sufficient_data_env_enabled(self) -> None:
        insufficient_payload = _ok_payload()
        insufficient_payload["sli"]["evaluation"]["ws"]["status"] = "insufficient_data"
        with patch.dict(
            "os.environ",
            {"SLO_GATE_REQUIRE_SUFFICIENT_DATA": "true"},
            clear=False,
        ), patch.object(_MODULE, "_fetch_json_payload", return_value=insufficient_payload):
            exit_code = main(["--url", "https://example.com/health/slo"])
        self.assertEqual(exit_code, 1)

    def test_main_can_fail_when_abuse_warn_env_enabled(self) -> None:
        warn_payload = _ok_payload()
        warn_payload["sli"]["abuse_economics"]["evaluation"]["status"] = "warn"
        with patch.dict(
            "os.environ",
            {"SLO_GATE_FAIL_ON_ABUSE_WARN": "true"},
            clear=False,
        ), patch.object(_MODULE, "_fetch_json_payload", return_value=warn_payload):
            exit_code = main(["--url", "https://example.com/health/slo"])
        self.assertEqual(exit_code, 1)

    def test_main_passes_with_payload_file_when_url_missing(self) -> None:
        payload = _ok_payload()
        with tempfile.TemporaryDirectory() as tmp_dir:
            payload_path = Path(tmp_dir) / "slo.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")
            with patch.dict(
                "os.environ",
                {
                    "SLO_GATE_HEALTH_SLO_URL": "",
                    "SLO_GATE_HEALTH_SLO_FILE": "",
                    "SLO_GATE_BEARER_TOKEN": "",
                },
                clear=False,
            ):
                exit_code = main(["--payload-file", str(payload_path)])
        self.assertEqual(exit_code, 0)

    def test_main_fails_when_payload_file_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            payload_path = Path(tmp_dir) / "slo.json"
            payload_path.write_text("{not-json}", encoding="utf-8")
            with patch.dict(
                "os.environ",
                {
                    "SLO_GATE_HEALTH_SLO_URL": "",
                    "SLO_GATE_HEALTH_SLO_FILE": "",
                    "SLO_GATE_BEARER_TOKEN": "",
                },
                clear=False,
            ):
                exit_code = main(["--payload-file", str(payload_path)])
        self.assertEqual(exit_code, 1)

    def test_main_writes_summary_file_for_missing_url_skip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary_path = Path(tmp_dir) / "slo-summary.json"
            with patch.dict(
                "os.environ",
                {
                    "SLO_GATE_HEALTH_SLO_URL": "",
                    "SLO_GATE_HEALTH_SLO_FILE": "",
                    "SLO_GATE_BEARER_TOKEN": "",
                },
                clear=False,
            ):
                exit_code = main(["--allow-missing-url", "--summary-path", str(summary_path)])
            self.assertEqual(exit_code, 0)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["result"], "skip")
        self.assertEqual(summary["reasons"], ["missing_url"])
        self.assertEqual(summary["statuses"]["ws"], "missing")
        self.assertEqual(summary["statuses"]["ws_burn_rate"], "missing")
        self.assertEqual(summary["statuses"]["ai_router_burn_rate"], "missing")
        self.assertEqual(summary["statuses"]["push"], "missing")
        self.assertEqual(summary["statuses"]["cuj"], "missing")
        self.assertEqual(summary["statuses"]["abuse_economics"], "missing")
        self.assertFalse(summary["url_configured"])

    def test_main_writes_summary_file_for_degraded_failure(self) -> None:
        degraded_payload = _ok_payload()
        degraded_payload["sli"]["evaluation"]["ws_burn_rate"]["status"] = "degraded"
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary_path = Path(tmp_dir) / "slo-summary.json"
            with patch.object(_MODULE, "_fetch_json_payload", return_value=degraded_payload):
                exit_code = main(
                    [
                        "--url",
                        "https://example.com/health/slo",
                        "--summary-path",
                        str(summary_path),
                    ]
                )
            self.assertEqual(exit_code, 1)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["result"], "fail")
        self.assertIn("ws_burn_rate_degraded", summary["reasons"])
        self.assertEqual(summary["statuses"]["ws"], "ok")
        self.assertEqual(summary["statuses"]["ws_burn_rate"], "degraded")
        self.assertEqual(summary["statuses"]["ai_router_burn_rate"], "ok")
        self.assertEqual(summary["statuses"]["push"], "ok")
        self.assertEqual(summary["statuses"]["cuj"], "ok")
        self.assertEqual(summary["statuses"]["abuse_economics"], "ok")
        self.assertTrue(summary["url_configured"])

    def test_main_writes_summary_file_for_payload_file_source(self) -> None:
        payload = _ok_payload()
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary_path = Path(tmp_dir) / "slo-summary.json"
            payload_path = Path(tmp_dir) / "slo.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")
            with patch.dict(
                "os.environ",
                {
                    "SLO_GATE_HEALTH_SLO_URL": "",
                    "SLO_GATE_HEALTH_SLO_FILE": "",
                    "SLO_GATE_BEARER_TOKEN": "",
                },
                clear=False,
            ):
                exit_code = main(
                    [
                        "--payload-file",
                        str(payload_path),
                        "--summary-path",
                        str(summary_path),
                    ]
                )
            self.assertEqual(exit_code, 0)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["result"], "pass")
        self.assertEqual(summary["source_type"], "file")
        self.assertTrue(summary["payload_file_configured"])
        self.assertFalse(summary["url_configured"])
        self.assertEqual(summary["statuses"]["abuse_economics"], "ok")


if __name__ == "__main__":
    unittest.main()
