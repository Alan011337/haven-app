from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.rate_limit_scope import (  # noqa: E402
    build_partner_pair_scope,
    build_rate_limit_scope_key,
    build_ws_message_scope_key,
    normalize_scope_component,
)


class RateLimitScopeBuilderTests(unittest.TestCase):
    def test_normalize_scope_component_truncates_and_falls_back(self) -> None:
        self.assertEqual(normalize_scope_component(""), "unknown")
        self.assertEqual(normalize_scope_component("  abc  "), "abc")
        self.assertEqual(len(normalize_scope_component("x" * 300)), 128)

    def test_partner_pair_scope_is_stable_order(self) -> None:
        user_a = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
        user_b = uuid.UUID("00000000-0000-0000-0000-0000000000bb")
        scope_ab = build_partner_pair_scope(user_id=user_a, partner_id=user_b)
        scope_ba = build_partner_pair_scope(user_id=user_b, partner_id=user_a)
        self.assertEqual(scope_ab, scope_ba)
        self.assertTrue(scope_ab.startswith("pair:"))

    def test_ws_message_scope_key_matches_dimension_flags(self) -> None:
        user_id = uuid.UUID("00000000-0000-0000-0000-000000000011")
        partner_id = uuid.UUID("00000000-0000-0000-0000-000000000022")
        key = build_ws_message_scope_key(
            user_id=user_id,
            partner_id=partner_id,
            client_ip="127.0.0.1",
            device_id="ios-123",
            include_ip=True,
            include_device=True,
            include_partner_pair=True,
        )
        self.assertIn(f"user:{user_id}", key)
        self.assertIn("ip:127.0.0.1", key)
        self.assertIn("device:ios-123", key)
        self.assertIn("pair:", key)

    def test_rate_limit_scope_key_format(self) -> None:
        key = build_rate_limit_scope_key(domain="journal", scope="ip", value="127.0.0.1")
        self.assertEqual(key, "journal:ip:127.0.0.1")


if __name__ == "__main__":
    unittest.main()
