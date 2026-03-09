import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.ai_router import (  # noqa: E402
    build_provider_chain,
    normalize_provider,
    normalize_router_task,
    select_analysis_route,
    select_task_route,
)


class AIRouterTests(unittest.TestCase):
    def test_normalize_provider_defaults_to_openai(self) -> None:
        self.assertEqual(normalize_provider(""), "openai")
        self.assertEqual(normalize_provider("unknown-provider"), "openai")

    def test_normalize_provider_accepts_supported_values(self) -> None:
        self.assertEqual(normalize_provider("openai"), "openai")
        self.assertEqual(normalize_provider("GEMINI"), "gemini")

    def test_normalize_router_task_defaults_to_l2_when_unknown(self) -> None:
        self.assertEqual(normalize_router_task(""), "l2_deep_reasoning")
        self.assertEqual(normalize_router_task("unknown-task"), "l2_deep_reasoning")
        self.assertEqual(normalize_router_task("L1_CLASSIFY_EXTRACT"), "l1_classify_extract")

    def test_build_provider_chain_primary_only_when_fallback_disabled(self) -> None:
        chain = build_provider_chain(
            primary_provider="openai",
            fallback_provider="gemini",
            fallback_enabled=False,
        )
        self.assertEqual(chain, ("openai",))

    def test_build_provider_chain_includes_fallback_when_enabled(self) -> None:
        chain = build_provider_chain(
            primary_provider="gemini",
            fallback_provider="openai",
            fallback_enabled=True,
        )
        self.assertEqual(chain, ("gemini", "openai"))

    def test_select_analysis_route_uses_configured_primary_gemini(self) -> None:
        with patch.object(settings, "AI_ROUTER_PRIMARY_PROVIDER", "gemini"), patch.object(
            settings, "AI_ROUTER_FALLBACK_PROVIDER", "openai"
        ), patch.object(settings, "AI_ROUTER_ENABLE_FALLBACK", True):
            route = select_analysis_route()
        self.assertEqual(route.selected_provider, "gemini")
        self.assertEqual(route.provider_chain, ("gemini", "openai"))
        self.assertEqual(route.reason, "configured_primary")

    def test_select_analysis_route_uses_configured_primary_openai(self) -> None:
        with patch.object(settings, "AI_ROUTER_PRIMARY_PROVIDER", "openai"), patch.object(
            settings, "AI_ROUTER_FALLBACK_PROVIDER", "gemini"
        ), patch.object(settings, "AI_ROUTER_ENABLE_FALLBACK", True):
            route = select_analysis_route()
        self.assertEqual(route.selected_provider, "openai")
        self.assertEqual(route.provider_chain, ("openai", "gemini"))
        self.assertEqual(route.reason, "configured_primary")

    def test_select_analysis_route_marks_unknown_primary_as_normalized(self) -> None:
        with patch.object(settings, "AI_ROUTER_PRIMARY_PROVIDER", "foo-provider"), patch.object(
            settings, "AI_ROUTER_FALLBACK_PROVIDER", "gemini"
        ), patch.object(settings, "AI_ROUTER_ENABLE_FALLBACK", True):
            route = select_analysis_route()
        self.assertEqual(route.selected_provider, "openai")
        self.assertEqual(route.provider_chain, ("openai", "gemini"))
        self.assertEqual(route.reason, "primary_provider_normalized_to_default")

    def test_select_task_route_uses_l1_primary_provider_when_configured(self) -> None:
        with patch.object(settings, "AI_ROUTER_PRIMARY_PROVIDER", "openai"), patch.object(
            settings, "AI_ROUTER_L1_PRIMARY_PROVIDER", "gemini"
        ), patch.object(settings, "AI_ROUTER_FALLBACK_PROVIDER", "openai"), patch.object(
            settings, "AI_ROUTER_ENABLE_FALLBACK", True
        ):
            route = select_task_route("l1_classify_extract")
        self.assertEqual(route.selected_provider, "gemini")
        self.assertEqual(route.provider_chain, ("gemini", "openai"))
        self.assertEqual(route.reason, "task_policy_l1")

    def test_select_task_route_uses_l2_primary_provider_when_configured(self) -> None:
        with patch.object(settings, "AI_ROUTER_PRIMARY_PROVIDER", "gemini"), patch.object(
            settings, "AI_ROUTER_L2_PRIMARY_PROVIDER", "openai"
        ), patch.object(settings, "AI_ROUTER_FALLBACK_PROVIDER", "gemini"), patch.object(
            settings, "AI_ROUTER_ENABLE_FALLBACK", True
        ):
            route = select_task_route("l2_deep_reasoning")
        self.assertEqual(route.selected_provider, "openai")
        self.assertEqual(route.provider_chain, ("openai", "gemini"))
        self.assertEqual(route.reason, "task_policy_l2")

    def test_select_task_route_unknown_task_normalizes_to_l2(self) -> None:
        with patch.object(settings, "AI_ROUTER_PRIMARY_PROVIDER", "openai"), patch.object(
            settings, "AI_ROUTER_L2_PRIMARY_PROVIDER", None
        ), patch.object(settings, "AI_ROUTER_FALLBACK_PROVIDER", "gemini"), patch.object(
            settings, "AI_ROUTER_ENABLE_FALLBACK", True
        ):
            route = select_task_route("unsupported-task")
        self.assertEqual(route.selected_provider, "openai")
        self.assertEqual(route.provider_chain, ("openai", "gemini"))
        self.assertEqual(route.reason, "task_policy_unknown_normalized_to_l2")


if __name__ == "__main__":
    unittest.main()
