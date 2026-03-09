from __future__ import annotations

import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.settings_domains import clear_settings_domain_cache  # noqa: E402
from app.services import pagination  # noqa: E402
from app.services.pagination import InvalidPageCursorError, PageCursor  # noqa: E402


class PaginationCursorSigningPolicyTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_settings_domain_cache()

    def test_cursor_encoding_rejects_missing_signing_key_in_fail_closed_mode(self) -> None:
        with patch.object(pagination.settings, "TIMELINE_CURSOR_REQUIRE_SIGNATURE", True), patch.object(
            pagination.settings, "TIMELINE_CURSOR_SIGNING_KEY", None
        ), patch.object(
            pagination.settings, "SECRET_KEY", ""
        ), patch.object(
            pagination.settings, "TIMELINE_CURSOR_ALLOW_DEFAULT_SIGNING_KEY", False
        ):
            clear_settings_domain_cache()
            with self.assertRaises(InvalidPageCursorError):
                PageCursor(
                    last_timestamp=datetime(2026, 3, 2, tzinfo=timezone.utc),
                    last_id=uuid.uuid4(),
                ).encode()

    def test_cursor_encoding_allows_insecure_fallback_only_when_explicitly_enabled(self) -> None:
        with patch.object(pagination.settings, "TIMELINE_CURSOR_REQUIRE_SIGNATURE", True), patch.object(
            pagination.settings, "TIMELINE_CURSOR_SIGNING_KEY", None
        ), patch.object(
            pagination.settings, "SECRET_KEY", ""
        ), patch.object(
            pagination.settings, "TIMELINE_CURSOR_ALLOW_DEFAULT_SIGNING_KEY", True
        ):
            clear_settings_domain_cache()
            encoded = PageCursor(
                last_timestamp=datetime(2026, 3, 2, tzinfo=timezone.utc),
                last_id=uuid.uuid4(),
            ).encode()
            self.assertIsNotNone(encoded)


if __name__ == "__main__":
    unittest.main()
