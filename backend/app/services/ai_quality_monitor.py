"""AI cost/quality drift monitoring helpers (P1-I baseline)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

EPSILON = 1e-9


@dataclass(frozen=True)
class AIQualityThresholds:
    schema_compliance_min: float
    hallucination_proxy_max: float
    drift_score_max: float
    cost_usd_per_active_couple_max: float


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_relative_drift_score(
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
    keys: tuple[str, ...],
) -> float:
    deltas: list[float] = []
    for key in keys:
        base = _safe_float(baseline.get(key))
        now = _safe_float(current.get(key))
        denom = max(abs(base), EPSILON)
        deltas.append(abs(now - base) / denom)

    if not deltas:
        return 0.0
    return sum(deltas) / float(len(deltas))


def evaluate_quality_gate(
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
    thresholds: AIQualityThresholds,
) -> dict[str, Any]:
    drift_score = calculate_relative_drift_score(
        baseline=baseline,
        current=current,
        keys=(
            "schema_compliance_rate",
            "hallucination_proxy_rate",
            "estimated_cost_usd_per_active_couple",
            "avg_tokens_per_analysis",
        ),
    )

    schema_compliance = _safe_float(current.get("schema_compliance_rate"))
    hallucination_proxy = _safe_float(current.get("hallucination_proxy_rate"))
    cost_per_active_couple = _safe_float(current.get("estimated_cost_usd_per_active_couple"))

    degraded_reasons: list[str] = []
    if schema_compliance < thresholds.schema_compliance_min:
        degraded_reasons.append("schema_compliance_below_min")
    if hallucination_proxy > thresholds.hallucination_proxy_max:
        degraded_reasons.append("hallucination_proxy_above_max")
    if cost_per_active_couple > thresholds.cost_usd_per_active_couple_max:
        degraded_reasons.append("cost_per_active_couple_above_max")
    if drift_score > thresholds.drift_score_max:
        degraded_reasons.append("drift_score_above_max")

    result = "degraded" if degraded_reasons else "pass"
    deterministic_gate_actions: list[str] = []
    if "cost_per_active_couple_above_max" in degraded_reasons:
        deterministic_gate_actions.append("switch_to_lower_cost_profile")
    if (
        "schema_compliance_below_min" in degraded_reasons
        or "hallucination_proxy_above_max" in degraded_reasons
        or "drift_score_above_max" in degraded_reasons
    ):
        deterministic_gate_actions.append("prefer_stable_profile")

    request_class_gate = {
        "journal_analysis": "red" if deterministic_gate_actions else "green",
        # Cooldown rewrite is less strict; only hard-red when hallucination/drift regress together.
        "cooldown_rewrite": (
            "red"
            if (
                "hallucination_proxy_above_max" in degraded_reasons
                and "drift_score_above_max" in degraded_reasons
            )
            else "green"
        ),
    }
    return {
        "result": result,
        "drift_score": round(drift_score, 6),
        "schema_compliance_rate": schema_compliance,
        "hallucination_proxy_rate": hallucination_proxy,
        "estimated_cost_usd_per_active_couple": cost_per_active_couple,
        "degraded_reasons": degraded_reasons,
        "deterministic_gate_actions": deterministic_gate_actions,
        "request_class_gate": request_class_gate,
    }
