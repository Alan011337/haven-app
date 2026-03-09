# backend/tests/test_notification_trigger_matrix.py
"""Tests for notification trigger matrix parsing and fallback behavior."""

import unittest
from unittest.mock import patch

from app.services.notification_trigger_matrix import (
    get_channels_for_event,
    get_throttle_window_seconds,
    is_channel_disabled,
    resolve_event_type,
    reset_matrix_cache_for_test,
)


class TestNotificationTriggerMatrix(unittest.TestCase):
    def setUp(self) -> None:
        reset_matrix_cache_for_test()

    def tearDown(self) -> None:
        reset_matrix_cache_for_test()

    def test_resolve_event_type_journal_alias(self) -> None:
        self.assertEqual(resolve_event_type("journal"), "journal_created")
        self.assertEqual(resolve_event_type("journal_created"), "journal_created")

    def test_resolve_event_type_card_passthrough(self) -> None:
        self.assertEqual(resolve_event_type("card_waiting"), "card_waiting")
        self.assertEqual(resolve_event_type("card_revealed"), "card_revealed")

    @patch("app.services.notification_trigger_matrix._load_matrix")
    def test_get_channels_for_event_journal_created(self, mock_load: object) -> None:
        mock_load.return_value = {
            "triggers": {
                "journal_created": {
                    "enabled": True,
                    "fallback_priority": ["push", "in_app_ws"],
                },
            },
            "kill_switch": {"global_disable": False, "per_channel_disable": {}},
        }
        import app.services.notification_trigger_matrix as m

        m._matrix_cache = None
        channels = get_channels_for_event("journal_created")
        self.assertEqual(channels, ["push", "in_app_ws"])

    @patch("app.services.notification_trigger_matrix._load_matrix")
    def test_get_channels_for_event_journal_alias(self, mock_load: object) -> None:
        mock_load.return_value = {
            "triggers": {
                "journal_created": {
                    "enabled": True,
                    "fallback_priority": ["push", "email", "in_app_ws"],
                },
            },
            "kill_switch": {"global_disable": False, "per_channel_disable": {}},
        }
        import app.services.notification_trigger_matrix as m

        m._matrix_cache = None
        channels = get_channels_for_event("journal")
        self.assertEqual(channels, ["push", "email", "in_app_ws"])

    @patch("app.services.notification_trigger_matrix._load_matrix")
    def test_get_channels_for_event_global_kill_switch(self, mock_load: object) -> None:
        mock_load.return_value = {
            "triggers": {
                "journal_created": {"enabled": True, "fallback_priority": ["push", "email"]},
            },
            "kill_switch": {"global_disable": True, "per_channel_disable": {}},
        }
        import app.services.notification_trigger_matrix as m

        m._matrix_cache = mock_load.return_value
        channels = get_channels_for_event("journal_created")
        self.assertEqual(channels, [])

    @patch("app.services.notification_trigger_matrix._load_matrix")
    def test_get_channels_for_event_per_channel_disable(self, mock_load: object) -> None:
        mock_load.return_value = {
            "triggers": {
                "card_waiting": {
                    "enabled": True,
                    "fallback_priority": ["push", "email", "in_app_ws"],
                },
            },
            "kill_switch": {
                "global_disable": False,
                "per_channel_disable": {"email": True},
            },
        }
        import app.services.notification_trigger_matrix as m

        m._matrix_cache = mock_load.return_value
        channels = get_channels_for_event("card_waiting")
        self.assertEqual(channels, ["push", "in_app_ws"])

    @patch("app.services.notification_trigger_matrix._load_matrix")
    def test_get_channels_for_event_disabled_trigger(self, mock_load: object) -> None:
        mock_load.return_value = {
            "triggers": {
                "card_revealed": {"enabled": False, "fallback_priority": ["push", "in_app_ws"]},
            },
            "kill_switch": {"global_disable": False, "per_channel_disable": {}},
        }
        import app.services.notification_trigger_matrix as m

        m._matrix_cache = mock_load.return_value
        channels = get_channels_for_event("card_revealed")
        self.assertEqual(channels, [])

    @patch("app.services.notification_trigger_matrix._load_matrix")
    def test_get_channels_for_event_unknown_trigger(self, mock_load: object) -> None:
        mock_load.return_value = {
            "triggers": {"journal_created": {"enabled": True, "fallback_priority": ["email"]}},
            "kill_switch": {"global_disable": False, "per_channel_disable": {}},
        }
        import app.services.notification_trigger_matrix as m

        m._matrix_cache = mock_load.return_value
        channels = get_channels_for_event("unknown_event")
        self.assertEqual(channels, [])

    @patch("app.services.notification_trigger_matrix._load_matrix")
    def test_get_throttle_window_seconds(self, mock_load: object) -> None:
        mock_load.return_value = {
            "triggers": {
                "journal_created": {"throttle_window_seconds": 60},
                "card_waiting": {"throttle_window_seconds": 0},
            },
            "kill_switch": {"global_disable": False, "per_channel_disable": {}},
        }
        import app.services.notification_trigger_matrix as m

        m._matrix_cache = mock_load.return_value
        self.assertEqual(get_throttle_window_seconds("journal_created"), 60)
        self.assertEqual(get_throttle_window_seconds("card_waiting"), 0)
        self.assertEqual(get_throttle_window_seconds("unknown"), 0)

    @patch("app.services.notification_trigger_matrix._load_matrix")
    def test_is_channel_disabled_global(self, mock_load: object) -> None:
        mock_load.return_value = {
            "kill_switch": {"global_disable": True, "per_channel_disable": {}},
        }
        import app.services.notification_trigger_matrix as m

        m._matrix_cache = mock_load.return_value
        self.assertTrue(is_channel_disabled("email"))
        self.assertTrue(is_channel_disabled("push"))

    @patch("app.services.notification_trigger_matrix._load_matrix")
    def test_is_channel_disabled_per_channel(self, mock_load: object) -> None:
        mock_load.return_value = {
            "kill_switch": {
                "global_disable": False,
                "per_channel_disable": {"push": True, "email": False},
            },
        }
        import app.services.notification_trigger_matrix as m

        m._matrix_cache = mock_load.return_value
        self.assertTrue(is_channel_disabled("push"))
        self.assertFalse(is_channel_disabled("email"))
