from __future__ import annotations

import unittest
import uuid
from unittest.mock import AsyncMock, patch

from app.services import notification_multichannel
from app.services.notification_runtime_metrics import notification_runtime_metrics


class NotificationMultichannelRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        notification_runtime_metrics.reset()

    async def test_dispatch_multichannel_keeps_bool_compatibility(self) -> None:
        with patch.object(
            notification_multichannel,
            "get_channels_for_event",
            return_value=["email", "in_app_ws", "push"],
        ), patch(
            "app.services.notification.is_email_notification_enabled",
            return_value=True,
        ), patch(
            "app.services.notification.send_partner_notification",
            AsyncMock(return_value=True),
        ), patch.object(
            notification_multichannel,
            "dispatch_in_app_ws",
            AsyncMock(
                return_value={
                    "success": False,
                    "reason": notification_multichannel.FAILURE_CHANNEL_DISABLED,
                }
            ),
        ), patch.object(
            notification_multichannel,
            "dispatch_push",
            AsyncMock(
                return_value={
                    "success": False,
                    "reason": notification_multichannel.FAILURE_NO_SUBSCRIPTIONS,
                }
            ),
        ):
            payload = await notification_multichannel.dispatch_multichannel(
                event_type="journal_created",
                receiver_email="partner@example.com",
                receiver_user_id=uuid.uuid4(),
                sender_name="Alex",
                action_type="journal",
            )

        self.assertEqual(
            payload,
            {
                "email": True,
                "in_app_ws": False,
                "push": False,
            },
        )
        counters = notification_runtime_metrics.snapshot()
        self.assertEqual(counters.get("notification_attempt_email_total"), 1)
        self.assertEqual(counters.get("notification_attempt_in_app_ws_total"), 1)
        self.assertEqual(counters.get("notification_attempt_push_total"), 1)
        self.assertEqual(counters.get("notification_success_email_total"), 1)
        self.assertEqual(counters.get("notification_failure_in_app_ws_total"), 1)
        self.assertEqual(
            counters.get("notification_failure_in_app_ws_channel_disabled_total"),
            1,
        )
        self.assertEqual(counters.get("notification_failure_push_total"), 1)
        self.assertEqual(
            counters.get("notification_failure_push_no_subscriptions_total"),
            1,
        )

    async def test_dispatch_multichannel_returns_detailed_results(self) -> None:
        with patch.object(
            notification_multichannel,
            "get_channels_for_event",
            return_value=["email", "in_app_ws", "push"],
        ), patch(
            "app.services.notification.is_email_notification_enabled",
            return_value=False,
        ):
            payload = await notification_multichannel.dispatch_multichannel(
                event_type="journal_created",
                receiver_email="partner@example.com",
                receiver_user_id=None,
                sender_name="Alex",
                action_type="journal",
                detailed=True,
            )

        self.assertEqual(
            payload,
            {
                "email": {
                    "success": False,
                    "reason": notification_multichannel.FAILURE_PROVIDER_UNAVAILABLE,
                },
                "in_app_ws": {
                    "success": False,
                    "reason": notification_multichannel.FAILURE_UNEXPECTED_ERROR,
                },
                "push": {
                    "success": False,
                    "reason": notification_multichannel.FAILURE_UNEXPECTED_ERROR,
                },
            },
        )
        counters = notification_runtime_metrics.snapshot()
        self.assertEqual(counters.get("notification_failure_email_provider_unavailable_total"), 1)
        self.assertEqual(counters.get("notification_failure_in_app_ws_unexpected_error_total"), 1)
        self.assertEqual(counters.get("notification_failure_push_unexpected_error_total"), 1)

    async def test_dispatch_in_app_ws_timeout_is_transport_error(self) -> None:
        with patch(
            "app.core.socket_manager.manager.send_personal_message",
            AsyncMock(side_effect=TimeoutError()),
        ):
            payload = await notification_multichannel.dispatch_in_app_ws(
                receiver_user_id=uuid.uuid4(),
                sender_name="Alex",
                action_type="journal",
            )
        self.assertEqual(
            payload,
            {
                "success": False,
                "reason": notification_multichannel.FAILURE_TRANSPORT_ERROR,
            },
        )


if __name__ == "__main__":
    unittest.main()
