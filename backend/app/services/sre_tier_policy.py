"""SRE-TIER-01: Service tier budget policy enforcement.

Defines Tier-0 (critical path) vs Tier-1 (important but non-blocking)
services and their error budget policies for the release gate.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TIER_POLICY_PATH = REPO_ROOT / "docs" / "sre" / "service-tier-policy.json"

TIER_0_SERVICES = [
    "auth",
    "journal_write",
    "card_draw",
    "card_respond",
    "pairing",
]

TIER_1_SERVICES = [
    "push_notification",
    "ai_analysis",
    "gamification",
    "growth_hooks",
    "admin",
]

DEFAULT_TIER_0_ERROR_BUDGET_PERCENT = 0.1  # 99.9% availability
DEFAULT_TIER_1_ERROR_BUDGET_PERCENT = 1.0  # 99.0% availability


def evaluate_tier_policy(
    *,
    health_payload: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate service tier budgets from health/SLO payload.

    Returns a dict with status (ok/degraded/insufficient_data)
    and per-tier evaluation results.
    """
    sli = health_payload.get("sli", {})
    if not isinstance(sli, dict):
        return {
            "status": "insufficient_data",
            "reason": "missing_sli_payload",
            "tiers": {},
        }

    # Extract key SLI signals
    cuj_sli = sli.get("cuj", {})
    cuj_metrics = cuj_sli.get("metrics", {}) if isinstance(cuj_sli, dict) else {}
    tier_results: dict[str, Any] = {
        "tier_0": {
            "services": TIER_0_SERVICES,
            "budget_percent": DEFAULT_TIER_0_ERROR_BUDGET_PERCENT,
            "status": "ok",
            "violations": [],
        },
        "tier_1": {
            "services": TIER_1_SERVICES,
            "budget_percent": DEFAULT_TIER_1_ERROR_BUDGET_PERCENT,
            "status": "ok",
            "violations": [],
        },
    }

    # Tier-0 checks
    ritual_rate = cuj_metrics.get("ritual_success_rate")
    if isinstance(ritual_rate, (int, float)) and ritual_rate < (1.0 - DEFAULT_TIER_0_ERROR_BUDGET_PERCENT / 100):
        tier_results["tier_0"]["violations"].append("ritual_success_below_tier0_budget")
        tier_results["tier_0"]["status"] = "degraded"

    bind_rate = cuj_metrics.get("partner_binding_success_rate")
    if isinstance(bind_rate, (int, float)) and bind_rate < (1.0 - DEFAULT_TIER_0_ERROR_BUDGET_PERCENT / 100):
        tier_results["tier_0"]["violations"].append("binding_success_below_tier0_budget")
        tier_results["tier_0"]["status"] = "degraded"

    overall_status = "ok"
    if tier_results["tier_0"]["status"] == "degraded":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "tiers": tier_results,
    }
