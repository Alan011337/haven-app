from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.feature_flags import resolve_feature_flags

DEFAULT_EXPERIMENT_KEY = "pricing_paywall_copy_v1"
DEFAULT_VARIANT_WEIGHTS: dict[str, int] = {
    "control": 50,
    "pricing_variant_a": 50,
}

_GUARDRAIL_THRESHOLD_MAP: dict[str, str] = {
    "pricing.experiment.refund_rate": "refund_rate_max",
    "pricing.experiment.chargeback_rate": "chargeback_rate_max",
    "pricing.experiment.p0_cuj_failure_rate": "p0_cuj_failure_rate_max",
    "pricing.experiment.support_ticket_rate": "support_ticket_rate_max",
}

_POLICY_PATH = Path(__file__).resolve().parents[3] / "docs" / "security" / "pricing-experiment-policy.json"


@dataclass(frozen=True)
class ExperimentDecision:
    eligible: bool
    variant: str
    reason: str
    bucket: int


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stable_bucket(*, user_id: str, experiment_key: str) -> int:
    digest = hashlib.sha256(f"{experiment_key}:{user_id}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def _pick_variant(*, bucket: int, weights: dict[str, int]) -> str:
    total = sum(weights.values())
    if total <= 0:
        return "control"
    running = 0
    target = bucket % total
    for name, weight in weights.items():
        running += weight
        if target < running:
            return name
    return next(iter(weights), "control")


def load_pricing_experiment_policy() -> dict[str, Any]:
    try:
        payload = json.loads(_POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    return payload if isinstance(payload, dict) else {}


def resolve_pricing_experiment_key(*, policy: dict[str, Any] | None = None) -> str:
    payload = policy if isinstance(policy, dict) else load_pricing_experiment_policy()
    value = payload.get("experiment_key")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_EXPERIMENT_KEY


def resolve_pricing_experiment_weights(
    *,
    policy: dict[str, Any] | None = None,
    override_weights: dict[str, int] | None = None,
) -> dict[str, int]:
    if override_weights:
        return normalize_variant_weights(override_weights)

    payload = policy if isinstance(policy, dict) else load_pricing_experiment_policy()
    raw_variants = payload.get("variants")
    normalized: dict[str, int] = {}
    if isinstance(raw_variants, list):
        for item in raw_variants:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            weight_value = _safe_int(item.get("weight"))
            if not name or weight_value is None or weight_value <= 0:
                continue
            normalized[name] = weight_value
    return normalize_variant_weights(normalized)


def resolve_pricing_guardrail_thresholds(*, policy: dict[str, Any] | None = None) -> dict[str, float]:
    payload = policy if isinstance(policy, dict) else load_pricing_experiment_policy()
    raw_policy = payload.get("guardrail_policy")
    thresholds: dict[str, float] = {}
    if isinstance(raw_policy, dict):
        for metric_name, threshold_key in _GUARDRAIL_THRESHOLD_MAP.items():
            parsed = _safe_float(raw_policy.get(threshold_key))
            if parsed is None or parsed <= 0:
                continue
            thresholds[metric_name] = parsed
    if len(thresholds) == len(_GUARDRAIL_THRESHOLD_MAP):
        return thresholds
    fallback = {
        "pricing.experiment.refund_rate": 0.03,
        "pricing.experiment.chargeback_rate": 0.01,
        "pricing.experiment.p0_cuj_failure_rate": 0.001,
        "pricing.experiment.support_ticket_rate": 0.05,
    }
    for key, value in fallback.items():
        thresholds.setdefault(key, value)
    return thresholds


def normalize_variant_weights(raw: dict[str, int] | None) -> dict[str, int]:
    if not raw:
        return dict(DEFAULT_VARIANT_WEIGHTS)
    normalized: dict[str, int] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        parsed = _safe_int(value)
        if parsed is None or parsed <= 0:
            continue
        normalized[key.strip()] = parsed
    return normalized or dict(DEFAULT_VARIANT_WEIGHTS)


def evaluate_pricing_experiment_decision(
    *,
    user_id: str,
    experiment_key: str,
    has_partner: bool,
    weights: dict[str, int] | None = None,
    policy: dict[str, Any] | None = None,
) -> ExperimentDecision:
    payload = policy if isinstance(policy, dict) else load_pricing_experiment_policy()
    canonical_experiment_key = resolve_pricing_experiment_key(policy=payload)
    requested_experiment_key = str(experiment_key or "").strip() or canonical_experiment_key

    resolved_flags = resolve_feature_flags(has_partner=has_partner)
    flags = resolved_flags.flags
    kill_switches = resolved_flags.kill_switches

    if kill_switches.get("disable_pricing_experiment", False):
        decision = ExperimentDecision(
            eligible=False,
            variant="control",
            reason="kill_switch:disable_pricing_experiment",
            bucket=0,
        )
        pricing_experiment_runtime_metrics.record_assignment(decision)
        return decision

    if requested_experiment_key != canonical_experiment_key:
        decision = ExperimentDecision(
            eligible=False,
            variant="control",
            reason="experiment_key_mismatch",
            bucket=0,
        )
        pricing_experiment_runtime_metrics.record_assignment(decision)
        return decision

    if not flags.get("growth_ab_experiment_enabled", False):
        decision = ExperimentDecision(
            eligible=False,
            variant="control",
            reason="flag_off:growth_ab_experiment_enabled",
            bucket=0,
        )
        pricing_experiment_runtime_metrics.record_assignment(decision)
        return decision

    if not flags.get("growth_pricing_experiment_enabled", False):
        decision = ExperimentDecision(
            eligible=False,
            variant="control",
            reason="flag_off:growth_pricing_experiment_enabled",
            bucket=0,
        )
        pricing_experiment_runtime_metrics.record_assignment(decision)
        return decision

    bucket = _stable_bucket(user_id=user_id, experiment_key=canonical_experiment_key)
    normalized_weights = resolve_pricing_experiment_weights(policy=payload, override_weights=weights)
    variant = _pick_variant(bucket=bucket, weights=normalized_weights)
    decision = ExperimentDecision(
        eligible=True,
        variant=variant,
        reason="eligible",
        bucket=bucket,
    )
    pricing_experiment_runtime_metrics.record_assignment(decision)
    return decision


def evaluate_pricing_experiment_guardrails(
    *,
    metric_values: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = policy if isinstance(policy, dict) else load_pricing_experiment_policy()
    thresholds = resolve_pricing_guardrail_thresholds(policy=payload)

    missing_metrics: list[str] = []
    breaches: list[dict[str, Any]] = []

    for metric_name, threshold in thresholds.items():
        parsed_value = _safe_float(metric_values.get(metric_name))
        if parsed_value is None:
            missing_metrics.append(metric_name)
            continue
        if parsed_value > threshold:
            breaches.append(
                {
                    "metric": metric_name,
                    "value": round(parsed_value, 8),
                    "threshold": round(threshold, 8),
                }
            )

    if len(missing_metrics) == len(thresholds):
        status = "insufficient_data"
    elif breaches:
        status = "triggered"
    else:
        status = "pass"

    result = {
        "status": status,
        "missing_metrics": sorted(missing_metrics),
        "breaches": breaches,
        "thresholds": thresholds,
        "checked_metrics_total": len(thresholds),
    }
    pricing_experiment_runtime_metrics.record_guardrail(result)
    return result


class PricingExperimentRuntimeMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._counts: dict[str, int] = {}
            self._assignment_reason_counts: dict[str, int] = {}
            self._assignment_variant_counts: dict[str, int] = {}
            self._guardrail_breach_counts: dict[str, int] = {}

    def _increment(self, key: str, value: int = 1) -> None:
        self._counts[key] = self._counts.get(key, 0) + value

    def _increment_reason(self, reason: str) -> None:
        normalized = reason.strip() if reason.strip() else "unknown"
        self._assignment_reason_counts[normalized] = self._assignment_reason_counts.get(normalized, 0) + 1

    def _increment_variant(self, variant: str) -> None:
        normalized = variant.strip() if variant.strip() else "unknown"
        self._assignment_variant_counts[normalized] = self._assignment_variant_counts.get(normalized, 0) + 1

    def _increment_breach(self, metric_name: str) -> None:
        normalized = metric_name.strip() if metric_name.strip() else "unknown"
        self._guardrail_breach_counts[normalized] = self._guardrail_breach_counts.get(normalized, 0) + 1

    def record_assignment(self, decision: ExperimentDecision) -> None:
        with self._lock:
            self._increment("pricing_experiment_assignment_total")
            self._increment_reason(decision.reason)
            self._increment_variant(decision.variant)
            if not decision.eligible:
                self._increment("pricing_experiment_assignment_ineligible_total")
            elif decision.variant == "control":
                self._increment("pricing_experiment_assignment_control_total")
            else:
                self._increment("pricing_experiment_assignment_variant_total")

    def record_guardrail(self, result: dict[str, Any]) -> None:
        status = str(result.get("status") or "").strip().lower()
        with self._lock:
            self._increment("pricing_experiment_guardrail_evaluations_total")
            if status == "pass":
                self._increment("pricing_experiment_guardrail_pass_total")
            elif status == "triggered":
                self._increment("pricing_experiment_guardrail_triggered_total")
            else:
                self._increment("pricing_experiment_guardrail_insufficient_data_total")

            breaches = result.get("breaches")
            if isinstance(breaches, list):
                for item in breaches:
                    if not isinstance(item, dict):
                        continue
                    metric_name = str(item.get("metric") or "").strip()
                    if metric_name:
                        self._increment_breach(metric_name)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counts": dict(self._counts),
                "assignment_reason_counts": dict(self._assignment_reason_counts),
                "assignment_variant_counts": dict(self._assignment_variant_counts),
                "guardrail_breach_counts": dict(self._guardrail_breach_counts),
            }


pricing_experiment_runtime_metrics = PricingExperimentRuntimeMetrics()
