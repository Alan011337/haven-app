#!/usr/bin/env python3
"""Dry-run assignment for pricing experiments (MON-04 skeleton)."""

from __future__ import annotations

import argparse
import json
import uuid

from app.services.pricing_experiment_runtime import (
    ExperimentDecision,
    evaluate_pricing_experiment_decision as _evaluate_runtime_decision,
    pricing_experiment_runtime_metrics,
    resolve_pricing_experiment_weights,
)


def evaluate_pricing_experiment_decision(
    *,
    user_id: str,
    experiment_key: str,
    has_partner: bool,
    weights: dict[str, int] | None = None,
) -> ExperimentDecision:
    normalized_weights = resolve_pricing_experiment_weights(override_weights=weights)
    return _evaluate_runtime_decision(
        user_id=user_id,
        experiment_key=experiment_key,
        has_partner=has_partner,
        weights=normalized_weights,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run pricing experiment assignment.")
    parser.add_argument("--user-id", required=True, help="User UUID for deterministic assignment.")
    parser.add_argument("--experiment-key", default="pricing_paywall_copy_v1")
    parser.add_argument("--has-partner", action="store_true", help="Resolve partner-dependent flags as true.")
    parser.add_argument(
        "--weights-json",
        default="",
        help='Optional JSON object, e.g. {"control":50,"pricing_variant_a":50}',
    )
    parser.add_argument(
        "--include-runtime-snapshot",
        action="store_true",
        help="Include pricing experiment runtime counters in output payload.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        parsed_user_id = str(uuid.UUID(str(args.user_id).strip()))
    except (ValueError, TypeError):
        print("[pricing-experiment-dry-run] fail: invalid --user-id (must be UUID)")
        return 1

    weights: dict[str, int] | None = None
    if args.weights_json.strip():
        try:
            raw = json.loads(args.weights_json)
            weights = raw if isinstance(raw, dict) else None
        except json.JSONDecodeError:
            print("[pricing-experiment-dry-run] fail: --weights-json must be valid JSON object")
            return 1

    decision = evaluate_pricing_experiment_decision(
        user_id=parsed_user_id,
        experiment_key=str(args.experiment_key).strip(),
        has_partner=bool(args.has_partner),
        weights=weights,
    )

    payload = {
        "experiment_key": str(args.experiment_key).strip(),
        "user_id": parsed_user_id,
        "has_partner": bool(args.has_partner),
        "eligible": decision.eligible,
        "variant": decision.variant,
        "reason": decision.reason,
        "bucket": decision.bucket,
    }
    if args.include_runtime_snapshot:
        payload["runtime_snapshot"] = pricing_experiment_runtime_metrics.snapshot()
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
