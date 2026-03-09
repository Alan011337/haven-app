import importlib.util
import ssl
import sys
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_observability_live_contract.py"
SPEC = importlib.util.spec_from_file_location("check_observability_live_contract", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_observability_live_contract_script_exists() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_observability_live_contract.py"
    assert script.exists(), "missing check_observability_live_contract.py"


def test_observability_live_contract_script_markers() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_observability_live_contract.py"
    text = script.read_text(encoding="utf-8")
    assert "--health-slo-url" in text
    assert "--allow-missing-url" in text
    assert "notification_runtime" in text
    assert "dynamic_content_runtime" in text
    assert "notification_outbox_depth" in text


class _FakeResponse:
    def __init__(self, payload: str) -> None:
        self._payload = payload
        self.status = 200

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._payload.encode("utf-8")


def test_fetch_payload_retries_with_certifi_context_on_ssl_verification_error() -> None:
    payload = '{"sli":{"notification_runtime":{},"dynamic_content_runtime":{}},"checks":{"notification_outbox_depth":{}}}'
    ssl_error = ssl.SSLCertVerificationError(
        1,
        "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)",
    )
    calls: list[object] = []

    def _fake_urlopen(request, timeout, context):  # type: ignore[no-untyped-def]
        calls.append(context)
        if len(calls) == 1:
            raise MODULE.urllib.error.URLError(ssl_error)
        return _FakeResponse(payload)

    with patch.object(MODULE, "_iter_ssl_contexts", return_value=["default_ctx", "certifi_ctx"]), patch.object(
        MODULE.urllib.request,
        "urlopen",
        side_effect=_fake_urlopen,
    ):
        result = MODULE._fetch_payload("https://example.com/health/slo", "", 10.0)

    assert result["sli"]["notification_runtime"] == {}
    assert calls == ["default_ctx", "certifi_ctx"]


def test_merge_checks_from_health_endpoint_uses_sibling_health_url() -> None:
    health_slo_payload = {
        "sli": {
            "notification_runtime": {},
            "dynamic_content_runtime": {},
        }
    }
    health_payload = {
        "checks": {
            "notification_outbox_depth": 0,
        }
    }

    with patch.object(
        MODULE,
        "_fetch_payload",
        return_value=health_payload,
    ) as fetch_mock:
        merged = MODULE._merge_checks_from_health_endpoint(
            health_slo_payload,
            health_slo_url="https://example.com/health/slo",
            bearer_token="",
            timeout_seconds=10.0,
        )

    assert merged["checks"]["notification_outbox_depth"] == 0
    fetch_mock.assert_called_once_with("https://example.com/health", "", 10.0)
