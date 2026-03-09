import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.feature_flags import (  # noqa: E402
    DEFAULT_FEATURE_FLAGS,
    DEFAULT_KILL_SWITCHES,
    resolve_feature_flags,
)


class FeatureFlagsServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_flags = settings.FEATURE_FLAGS_JSON
        self.original_kill_switches = settings.FEATURE_KILL_SWITCHES_JSON

    def tearDown(self) -> None:
        settings.FEATURE_FLAGS_JSON = self.original_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_kill_switches

    def test_resolve_feature_flags_applies_json_overrides(self) -> None:
        settings.FEATURE_FLAGS_JSON = (
            '{"growth_referral_enabled": true, '
            '"growth_ab_experiment_enabled": true, '
            '"growth_pricing_experiment_enabled": true}'
        )
        settings.FEATURE_KILL_SWITCHES_JSON = "{}"
        resolved = resolve_feature_flags(has_partner=True)
        self.assertTrue(resolved.flags["growth_referral_enabled"])
        self.assertTrue(resolved.flags["growth_ab_experiment_enabled"])
        self.assertTrue(resolved.flags["growth_pricing_experiment_enabled"])
        self.assertEqual(resolved.kill_switches["disable_referral_funnel"], False)
        self.assertEqual(resolved.kill_switches["disable_growth_ab_experiment"], False)
        self.assertEqual(resolved.kill_switches["disable_pricing_experiment"], False)
        self.assertEqual(resolved.kill_switches["disable_growth_reengagement_hooks"], False)
        self.assertEqual(resolved.kill_switches["disable_growth_activation_dashboard"], False)
        self.assertEqual(resolved.kill_switches["disable_growth_onboarding_quest"], False)
        self.assertEqual(resolved.kill_switches["disable_growth_sync_nudges"], False)
        self.assertEqual(resolved.kill_switches["disable_growth_first_delight"], False)

    def test_kill_switch_disables_target_flag(self) -> None:
        settings.FEATURE_FLAGS_JSON = '{"growth_referral_enabled": true, "growth_pricing_experiment_enabled": true}'
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_referral_funnel": true, "disable_pricing_experiment": true}'
        resolved = resolve_feature_flags(has_partner=True)
        self.assertTrue(resolved.kill_switches["disable_referral_funnel"])
        self.assertTrue(resolved.kill_switches["disable_pricing_experiment"])
        self.assertFalse(resolved.flags["growth_referral_enabled"])
        self.assertFalse(resolved.flags["growth_pricing_experiment_enabled"])

    def test_additional_growth_kill_switches_disable_target_flags(self) -> None:
        settings.FEATURE_FLAGS_JSON = (
            '{"growth_ab_experiment_enabled": true, '
            '"growth_reengagement_hooks_enabled": true, '
            '"growth_activation_dashboard_enabled": true, '
            '"growth_onboarding_quest_enabled": true, '
            '"growth_sync_nudges_enabled": true, '
            '"growth_first_delight_enabled": true}'
        )
        settings.FEATURE_KILL_SWITCHES_JSON = (
            '{"disable_growth_ab_experiment": true, '
            '"disable_growth_reengagement_hooks": true, '
            '"disable_growth_activation_dashboard": true, '
            '"disable_growth_onboarding_quest": true, '
            '"disable_growth_sync_nudges": true, '
            '"disable_growth_first_delight": true}'
        )

        resolved = resolve_feature_flags(has_partner=True)
        self.assertFalse(resolved.flags["growth_ab_experiment_enabled"])
        self.assertFalse(resolved.flags["growth_reengagement_hooks_enabled"])
        self.assertFalse(resolved.flags["growth_activation_dashboard_enabled"])
        self.assertFalse(resolved.flags["growth_onboarding_quest_enabled"])
        self.assertFalse(resolved.flags["growth_sync_nudges_enabled"])
        self.assertFalse(resolved.flags["growth_first_delight_enabled"])

    def test_weekly_review_and_repair_flow_flags_are_togglable(self) -> None:
        settings.FEATURE_FLAGS_JSON = '{"weekly_review_v1": true, "repair_flow_v1": true}'
        settings.FEATURE_KILL_SWITCHES_JSON = (
            '{"disable_weekly_review_v1": true, "disable_repair_flow_v1": false}'
        )
        resolved = resolve_feature_flags(has_partner=True)
        self.assertFalse(resolved.flags["weekly_review_v1"])
        self.assertTrue(resolved.flags["repair_flow_v1"])
        self.assertTrue(resolved.kill_switches["disable_weekly_review_v1"])
        self.assertFalse(resolved.kill_switches["disable_repair_flow_v1"])

    def test_runtime_channel_flags_and_kill_switches_are_supported(self) -> None:
        settings.FEATURE_FLAGS_JSON = (
            '{"websocket_realtime_enabled": true, '
            '"webpush_enabled": true, '
            '"email_notifications_enabled": true, '
            '"timeline_cursor_enabled": true, '
            '"safety_mode_enabled": true}'
        )
        settings.FEATURE_KILL_SWITCHES_JSON = (
            '{"disable_websocket_realtime": true, '
            '"disable_webpush": true, '
            '"disable_email_notifications": true, '
            '"disable_timeline_cursor": true, '
            '"disable_safety_mode": true}'
        )
        resolved = resolve_feature_flags(has_partner=True)
        self.assertFalse(resolved.flags["websocket_realtime_enabled"])
        self.assertFalse(resolved.flags["webpush_enabled"])
        self.assertFalse(resolved.flags["email_notifications_enabled"])
        self.assertFalse(resolved.flags["timeline_cursor_enabled"])
        self.assertFalse(resolved.flags["safety_mode_enabled"])

    def test_invalid_json_falls_back_to_defaults(self) -> None:
        settings.FEATURE_FLAGS_JSON = "{bad-json"
        settings.FEATURE_KILL_SWITCHES_JSON = "[]"
        resolved = resolve_feature_flags(has_partner=True)
        self.assertEqual(resolved.flags, DEFAULT_FEATURE_FLAGS)
        self.assertEqual(resolved.kill_switches, DEFAULT_KILL_SWITCHES)

    def test_has_partner_false_disables_partner_dependent_growth_flags(self) -> None:
        settings.FEATURE_FLAGS_JSON = '{"growth_referral_enabled": true, "growth_reengagement_hooks_enabled": true}'
        settings.FEATURE_KILL_SWITCHES_JSON = "{}"
        resolved = resolve_feature_flags(has_partner=False)
        self.assertFalse(resolved.flags["growth_referral_enabled"])
        self.assertFalse(resolved.flags["growth_reengagement_hooks_enabled"])


if __name__ == "__main__":
    unittest.main()
