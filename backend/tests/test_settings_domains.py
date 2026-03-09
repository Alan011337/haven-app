from __future__ import annotations

import unittest

from app.core.settings_domains import (
    clear_settings_domain_cache,
    get_dynamic_content_settings,
    get_billing_webhook_settings,
    get_notification_outbox_settings,
    get_push_dispatch_settings,
    get_timeline_cursor_settings,
    get_ws_settings,
    load_dynamic_content_settings,
    load_billing_webhook_settings,
    load_notification_outbox_settings,
    load_push_dispatch_settings,
    load_timeline_cursor_settings,
    load_ws_settings,
)
from app.core.config import settings


class _Source:
    pass


class SettingsDomainsTests(unittest.TestCase):
    def test_load_ws_settings_applies_guards(self) -> None:
        source = _Source()
        source.WS_MAX_CONNECTIONS_PER_USER = 0
        source.WS_MESSAGE_RATE_LIMIT_COUNT = "240"
        source.WS_MESSAGE_SCOPE_INCLUDE_IP = "false"
        source.WS_CONNECTION_RATE_LIMIT_WINDOW_SECONDS = -10
        source.WS_SEND_TIMEOUT_SECONDS = "0.001"
        source.WS_SEND_LOCK_WAIT_SECONDS = "0.0"
        source.WS_MAX_PENDING_SENDS_PER_USER = 0

        result = load_ws_settings(source)
        self.assertEqual(result.max_connections_per_user, 1)
        self.assertEqual(result.message_rate_limit_count, 240)
        self.assertFalse(result.scope_include_ip)
        self.assertEqual(result.connection_rate_limit_window_seconds, 1)
        self.assertEqual(result.send_timeout_seconds, 0.05)
        self.assertEqual(result.send_lock_wait_seconds, 0.01)
        self.assertEqual(result.max_pending_sends_per_user, 1)

    def test_load_push_dispatch_settings_clamps_batch_size(self) -> None:
        source = _Source()
        source.PUSH_DISPATCH_MAX_ACTIVE_SUBSCRIPTIONS = 10
        source.PUSH_DISPATCH_BATCH_SIZE = 100
        source.PUSH_DISPATCH_RETRY_ATTEMPTS = "2"
        source.PUSH_DISPATCH_RETRY_BASE_SECONDS = "0.5"

        result = load_push_dispatch_settings(source)
        self.assertEqual(result.max_active_subscriptions, 10)
        self.assertEqual(result.batch_size, 10)
        self.assertEqual(result.retry_attempts, 2)
        self.assertEqual(result.retry_base_seconds, 0.5)

    def test_load_billing_webhook_settings_enforces_min_values(self) -> None:
        source = _Source()
        source.BILLING_WEBHOOK_RETRY_MAX_ATTEMPTS = 0
        source.BILLING_WEBHOOK_RETRY_BASE_SECONDS = 0
        source.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS = "30"
        source.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = "true"

        result = load_billing_webhook_settings(source)
        self.assertEqual(result.retry_max_attempts, 1)
        self.assertEqual(result.retry_base_seconds, 1)
        self.assertEqual(result.signature_tolerance_seconds, 30)
        self.assertTrue(result.async_mode)

    def test_load_timeline_cursor_settings_parses_signing_policy(self) -> None:
        source = _Source()
        source.TIMELINE_CURSOR_MAX_LIMIT = "250"
        source.TIMELINE_CURSOR_QUERY_BUDGET = "1000"
        source.TIMELINE_CURSOR_SIGNING_KEY = "  cursor-key  "
        source.TIMELINE_CURSOR_REQUIRE_SIGNATURE = "true"
        source.TIMELINE_CURSOR_ALLOW_DEFAULT_SIGNING_KEY = "false"

        result = load_timeline_cursor_settings(source)
        self.assertEqual(result.max_limit, 250)
        self.assertEqual(result.query_budget, 1000)
        self.assertEqual(result.signing_key, "cursor-key")
        self.assertTrue(result.require_signature)
        self.assertFalse(result.allow_default_signing_key)

    def test_load_notification_outbox_settings_parses_runtime_contract(self) -> None:
        source = _Source()
        source.NOTIFICATION_OUTBOX_MAX_ATTEMPTS = "5"
        source.NOTIFICATION_OUTBOX_RETRY_BASE_SECONDS = "12"
        source.NOTIFICATION_OUTBOX_CLAIM_LIMIT = "80"
        source.NOTIFICATION_OUTBOX_DISPATCH_LOCK_NAME = "  outbox-main "
        source.NOTIFICATION_OUTBOX_AUTO_REPLAY_MIN_DEAD_LETTER_RATE = "0.55"
        source.NOTIFICATION_OUTBOX_BACKLOG_THROTTLE_ENABLED = "true"
        source.NOTIFICATION_OUTBOX_BACKLOG_THROTTLE_DEPTH_THRESHOLD = "900"
        source.NOTIFICATION_OUTBOX_BACKLOG_THROTTLE_OLDEST_PENDING_SECONDS_THRESHOLD = "1500"
        source.NOTIFICATION_OUTBOX_BACKLOG_THROTTLE_EXEMPT_EVENT_TYPES = "partner_bound,repair_started"
        source.NOTIFICATION_OUTBOX_BACKLOG_THROTTLE_EXEMPT_ACTION_TYPES = "journal,active_care"

        result = load_notification_outbox_settings(source)
        self.assertEqual(result.max_attempts, 5)
        self.assertEqual(result.retry_base_seconds, 12)
        self.assertEqual(result.claim_limit, 80)
        self.assertEqual(result.dispatch_lock_name, "outbox-main")
        self.assertEqual(result.auto_replay_min_dead_letter_rate, 0.55)
        self.assertTrue(result.backlog_throttle_enabled)
        self.assertEqual(result.backlog_throttle_depth_threshold, 900)
        self.assertEqual(result.backlog_throttle_oldest_pending_seconds_threshold, 1500)
        self.assertEqual(result.backlog_throttle_exempt_event_types, ("partner_bound", "repair_started"))
        self.assertEqual(result.backlog_throttle_exempt_action_types, ("journal", "active_care"))

    def test_load_dynamic_content_settings_parses_runtime_contract(self) -> None:
        source = _Source()
        source.DYNAMIC_CONTENT_AI_TIMEOUT_SECONDS = "8.5"
        source.DYNAMIC_CONTENT_AI_MAX_RETRIES = "3"
        source.DYNAMIC_CONTENT_SHADOW_MODE = "true"
        source.DYNAMIC_CONTENT_DEGRADED_FALLBACK_RATIO_THRESHOLD = "0.7"

        result = load_dynamic_content_settings(source)
        self.assertEqual(result.ai_timeout_seconds, 8.5)
        self.assertEqual(result.ai_max_retries, 3)
        self.assertTrue(result.shadow_mode)
        self.assertEqual(result.degraded_fallback_ratio_threshold, 0.7)

    def test_get_ws_settings_cache_refresh(self) -> None:
        clear_settings_domain_cache()
        original = settings.WS_MAX_CONNECTIONS_PER_USER
        try:
            settings.WS_MAX_CONNECTIONS_PER_USER = 7
            first = get_ws_settings()
            self.assertEqual(first.max_connections_per_user, 7)

            cached = get_ws_settings()
            self.assertEqual(cached.max_connections_per_user, 7)
            self.assertIs(first, cached)

            settings.WS_MAX_CONNECTIONS_PER_USER = 9
            refreshed_from_value_change = get_ws_settings()
            self.assertEqual(refreshed_from_value_change.max_connections_per_user, 9)
            self.assertIsNot(cached, refreshed_from_value_change)

            clear_settings_domain_cache()
            refreshed = get_ws_settings()
            self.assertEqual(refreshed.max_connections_per_user, 9)
        finally:
            settings.WS_MAX_CONNECTIONS_PER_USER = original
            clear_settings_domain_cache()

    def test_get_push_dispatch_settings_cache_refresh(self) -> None:
        clear_settings_domain_cache()
        original_max_active = settings.PUSH_DISPATCH_MAX_ACTIVE_SUBSCRIPTIONS
        try:
            settings.PUSH_DISPATCH_MAX_ACTIVE_SUBSCRIPTIONS = 11
            first = get_push_dispatch_settings()
            self.assertEqual(first.max_active_subscriptions, 11)

            cached = get_push_dispatch_settings()
            self.assertIs(first, cached)

            settings.PUSH_DISPATCH_MAX_ACTIVE_SUBSCRIPTIONS = 7
            refreshed = get_push_dispatch_settings()
            self.assertEqual(refreshed.max_active_subscriptions, 7)
            self.assertIsNot(cached, refreshed)
        finally:
            settings.PUSH_DISPATCH_MAX_ACTIVE_SUBSCRIPTIONS = original_max_active
            clear_settings_domain_cache()

    def test_get_billing_webhook_settings_cache_refresh(self) -> None:
        clear_settings_domain_cache()
        original_async = settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE
        try:
            settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = False
            first = get_billing_webhook_settings()
            self.assertFalse(first.async_mode)

            cached = get_billing_webhook_settings()
            self.assertIs(first, cached)

            settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = True
            refreshed = get_billing_webhook_settings()
            self.assertTrue(refreshed.async_mode)
            self.assertIsNot(cached, refreshed)
        finally:
            settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = original_async
            clear_settings_domain_cache()

    def test_get_timeline_cursor_settings_cache_refresh(self) -> None:
        clear_settings_domain_cache()
        original_budget = settings.TIMELINE_CURSOR_QUERY_BUDGET
        try:
            settings.TIMELINE_CURSOR_QUERY_BUDGET = 400
            first = get_timeline_cursor_settings()
            self.assertEqual(first.query_budget, 400)
            cached = get_timeline_cursor_settings()
            self.assertIs(first, cached)

            settings.TIMELINE_CURSOR_QUERY_BUDGET = 900
            refreshed = get_timeline_cursor_settings()
            self.assertEqual(refreshed.query_budget, 900)
            self.assertIsNot(cached, refreshed)
        finally:
            settings.TIMELINE_CURSOR_QUERY_BUDGET = original_budget
            clear_settings_domain_cache()

    def test_get_notification_outbox_settings_cache_refresh(self) -> None:
        clear_settings_domain_cache()
        original_claim_limit = settings.NOTIFICATION_OUTBOX_CLAIM_LIMIT
        try:
            settings.NOTIFICATION_OUTBOX_CLAIM_LIMIT = 60
            first = get_notification_outbox_settings()
            self.assertEqual(first.claim_limit, 60)
            cached = get_notification_outbox_settings()
            self.assertIs(first, cached)

            settings.NOTIFICATION_OUTBOX_CLAIM_LIMIT = 20
            refreshed = get_notification_outbox_settings()
            self.assertEqual(refreshed.claim_limit, 20)
            self.assertIsNot(cached, refreshed)
        finally:
            settings.NOTIFICATION_OUTBOX_CLAIM_LIMIT = original_claim_limit
            clear_settings_domain_cache()

    def test_get_dynamic_content_settings_cache_refresh(self) -> None:
        clear_settings_domain_cache()
        original_timeout = settings.DYNAMIC_CONTENT_AI_TIMEOUT_SECONDS
        try:
            settings.DYNAMIC_CONTENT_AI_TIMEOUT_SECONDS = 12.5
            first = get_dynamic_content_settings()
            self.assertEqual(first.ai_timeout_seconds, 12.5)
            cached = get_dynamic_content_settings()
            self.assertIs(first, cached)

            settings.DYNAMIC_CONTENT_AI_TIMEOUT_SECONDS = 3.0
            refreshed = get_dynamic_content_settings()
            self.assertEqual(refreshed.ai_timeout_seconds, 3.0)
            self.assertIsNot(cached, refreshed)
        finally:
            settings.DYNAMIC_CONTENT_AI_TIMEOUT_SECONDS = original_timeout
            clear_settings_domain_cache()


if __name__ == "__main__":
    unittest.main()
