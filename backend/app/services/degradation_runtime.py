"""DEG-01/DEG-02: Degradation runtime for graceful service degradation.

Provides per-feature degradation status based on health endpoint signals.
Frontend can poll this to show degradation banners.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Feature-level degradation configuration
DEGRADATION_FEATURES = {
    "journal_write": {
        "fallback": "Journal will be saved locally and synced when service recovers.",
        "severity": "warning",
    },
    "ai_analysis": {
        "fallback": "AI analysis is temporarily unavailable. Your journal is saved.",
        "severity": "info",
    },
    "card_draw": {
        "fallback": "Card draw may be slower than usual.",
        "severity": "warning",
    },
    "push_notification": {
        "fallback": "Notifications may be delayed.",
        "severity": "info",
    },
    "partner_sync": {
        "fallback": "Partner updates may be delayed.",
        "severity": "info",
    },
}


def evaluate_degradation_status(
    *,
    health_payload: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate per-feature degradation based on health payload.

    Returns a dict of feature -> degradation info for the frontend.
    """
    sli = health_payload.get("sli", {})
    if not isinstance(sli, dict):
        return {"status": "unknown", "features": {}}

    evaluation = sli.get("evaluation", {})
    if not isinstance(evaluation, dict):
        return {"status": "ok", "features": {}}

    degraded_features: dict[str, Any] = {}

    # Check CUJ SLI
    cuj_eval = evaluation.get("cuj", {})
    if isinstance(cuj_eval, dict) and cuj_eval.get("status") == "degraded":
        reasons = cuj_eval.get("reasons", [])
        if any("ritual" in r for r in reasons):
            degraded_features["card_draw"] = DEGRADATION_FEATURES["card_draw"]
        if any("journal" in r for r in reasons):
            degraded_features["journal_write"] = DEGRADATION_FEATURES["journal_write"]
        if any("binding" in r for r in reasons):
            degraded_features["partner_sync"] = DEGRADATION_FEATURES["partner_sync"]

    # Check Push SLI
    push_eval = evaluation.get("push", {})
    if isinstance(push_eval, dict) and push_eval.get("status") == "degraded":
        degraded_features["push_notification"] = DEGRADATION_FEATURES["push_notification"]

    # Check WS SLI
    ws_eval = evaluation.get("ws", {})
    if isinstance(ws_eval, dict) and ws_eval.get("status") == "degraded":
        degraded_features["partner_sync"] = DEGRADATION_FEATURES["partner_sync"]

    overall = "degraded" if degraded_features else "ok"
    return {
        "status": overall,
        "features": degraded_features,
    }
