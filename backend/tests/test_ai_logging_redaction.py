import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import ai as ai_module  # noqa: E402


class AiLoggingRedactionTests(unittest.IsolatedAsyncioTestCase):
    async def test_moderation_precheck_log_masks_exception_details(self) -> None:
        fake_client = SimpleNamespace(
            moderations=SimpleNamespace(
                create=AsyncMock(side_effect=RuntimeError("redis://:super-secret@redis.internal:6379/0"))
            )
        )
        with patch.object(ai_module, "client", fake_client):
            with self.assertLogs(ai_module.logger, level="CRITICAL") as captured:
                signal, was_error = await ai_module._run_moderation_precheck("hello")

        self.assertIsNone(signal)
        self.assertTrue(was_error)
        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("redis://", merged)

    async def test_analyze_journal_log_masks_exception_details(self) -> None:
        fake_client = SimpleNamespace(
            beta=SimpleNamespace(
                chat=SimpleNamespace(
                    completions=SimpleNamespace(
                        parse=AsyncMock(
                            side_effect=RuntimeError(
                                "postgresql://svc:super-secret@db.internal:5432/haven unavailable"
                            )
                        )
                    )
                )
            )
        )
        with patch.object(ai_module, "_run_moderation_precheck", AsyncMock(return_value=(None, False))):
            with patch.object(ai_module, "client", fake_client):
                with self.assertLogs(ai_module.logger, level="WARNING") as captured:
                    fallback = await ai_module.analyze_journal("test-content")

        self.assertFalse(fallback["parse_success"])
        merged = "\n".join(captured.output)
        self.assertIn("AI provider fallback exhausted", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("postgresql://", merged)


if __name__ == "__main__":
    unittest.main()
