import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import ai as ai_module  # noqa: E402
from app.services.ai_router import AIProviderError  # noqa: E402


def _analysis_messages() -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "test journal"},
    ]


class _FakeResponse:
    def __init__(self, *, status_code: int, json_payload=None, json_error: Exception | None = None) -> None:
        self.status_code = status_code
        self._json_payload = json_payload
        self._json_error = json_error

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._json_payload


class _FakeAsyncClient:
    """Mock httpx.AsyncClient that supports both context-manager and direct usage."""
    is_closed = False  # 🚀 Support reusable client check

    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return self._response


class GeminiAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_gemini_api_key_raises_provider_error(self) -> None:
        with patch.object(ai_module.settings, "GEMINI_API_KEY", ""):
            with self.assertRaises(AIProviderError) as ctx:
                await ai_module._analyze_with_gemini_provider(
                    analysis_messages=_analysis_messages(),
                    temperature=0.7,
                )
        self.assertEqual(ctx.exception.provider, "gemini")
        self.assertEqual(ctx.exception.reason, "missing_api_key")
        self.assertFalse(ctx.exception.retryable)

    async def test_invalid_json_response_raises_provider_error(self) -> None:
        response = _FakeResponse(status_code=200, json_error=ValueError("bad json"))

        with patch.object(ai_module.settings, "GEMINI_API_KEY", "gemini-test-key"):
            with patch.object(
                ai_module,
                "_gemini_http_client",
                _FakeAsyncClient(response),
            ):
                with self.assertRaises(AIProviderError) as ctx:
                    await ai_module._analyze_with_gemini_provider(
                        analysis_messages=_analysis_messages(),
                        temperature=0.7,
                    )
        self.assertEqual(ctx.exception.reason, "invalid_json_response")

    async def test_empty_content_text_raises_provider_error(self) -> None:
        payload = {
            "candidates": [{"content": {"parts": [{"text": ""}]}}],
            "modelVersion": "gemini-2.0-flash-lite",
        }
        response = _FakeResponse(status_code=200, json_payload=payload)

        with patch.object(ai_module.settings, "GEMINI_API_KEY", "gemini-test-key"):
            with patch.object(
                ai_module,
                "_gemini_http_client",
                _FakeAsyncClient(response),
            ):
                with self.assertRaises(AIProviderError) as ctx:
                    await ai_module._analyze_with_gemini_provider(
                        analysis_messages=_analysis_messages(),
                        temperature=0.7,
                    )
        self.assertEqual(ctx.exception.reason, "missing_content_text")

    async def test_invalid_schema_text_raises_provider_error(self) -> None:
        payload = {
            "candidates": [{"content": {"parts": [{"text": "{\"unexpected\":\"shape\"}"}]}}],
            "modelVersion": "gemini-2.0-flash-lite",
        }
        response = _FakeResponse(status_code=200, json_payload=payload)

        with patch.object(ai_module.settings, "GEMINI_API_KEY", "gemini-test-key"):
            with patch.object(
                ai_module,
                "_gemini_http_client",
                _FakeAsyncClient(response),
            ):
                with self.assertRaises(AIProviderError) as ctx:
                    await ai_module._analyze_with_gemini_provider(
                        analysis_messages=_analysis_messages(),
                        temperature=0.7,
                    )
        self.assertEqual(ctx.exception.reason, "schema_validation_failed")

    async def test_status_5xx_raises_retryable_provider_error(self) -> None:
        response = _FakeResponse(status_code=503, json_payload={"error": "unavailable"})

        with patch.object(ai_module.settings, "GEMINI_API_KEY", "gemini-test-key"):
            with patch.object(
                ai_module,
                "_gemini_http_client",
                _FakeAsyncClient(response),
            ):
                with self.assertRaises(AIProviderError) as ctx:
                    await ai_module._analyze_with_gemini_provider(
                        analysis_messages=_analysis_messages(),
                        temperature=0.7,
                    )
        self.assertEqual(ctx.exception.reason, "status_5xx")
        self.assertTrue(ctx.exception.retryable)
        self.assertEqual(ctx.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
