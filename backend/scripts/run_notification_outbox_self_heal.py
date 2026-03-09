#!/usr/bin/env python3
"""Generate deterministic outbox self-heal actions from outbox health snapshot."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--policy",
        default=str(Path(__file__).resolve().parents[1] / "config" / "notification_outbox_self_heal_policy.json"),
        help="Policy JSON path for thresholds/action toggles.",
    )
    parser.add_argument(
        "--snapshot",
        default="/tmp/notification-outbox-health-snapshot-local.json",
        help="Outbox health snapshot path.",
    )
    parser.add_argument("--warn-depth-threshold", type=float, default=None)
    parser.add_argument("--critical-depth-threshold", type=float, default=None)
    parser.add_argument("--warn-dead-rate-threshold", type=float, default=None)
    parser.add_argument("--critical-dead-rate-threshold", type=float, default=None)
    parser.add_argument("--output", default="/tmp/notification-outbox-self-heal-summary.json")
    parser.add_argument("--allow-missing-snapshot", action="store_true")
    parser.add_argument(
        "--apply-safe-actions",
        action="store_true",
        help="Execute safe remediation actions (reclaim/replay) after plan generation.",
    )
    parser.add_argument(
        "--recovery-replay-limit",
        type=int,
        default=100,
        help="Replay limit when apply-safe-actions triggers dead-letter replay.",
    )
    return parser


def _safe_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def _load_policy(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_threshold(args_value: float, policy: dict[str, Any], key: str, fallback: float) -> float:
    if args_value is not None:
        return float(args_value)
    thresholds = policy.get("thresholds")
    if isinstance(thresholds, dict):
        raw = thresholds.get(key)
        if isinstance(raw, (int, float)):
            return float(raw)
    return float(fallback)


def _is_action_enabled(policy: dict[str, Any], key: str, *, default: bool = True) -> bool:
    actions = policy.get("actions")
    if not isinstance(actions, dict):
        return default
    raw = actions.get(key)
    if isinstance(raw, bool):
        return raw
    return default


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    policy_path = Path(args.policy).resolve()
    policy = _load_policy(policy_path)
    snapshot_path = Path(args.snapshot).resolve()
    output_path = Path(args.output).resolve()
    warn_depth_threshold = _resolve_threshold(args.warn_depth_threshold, policy, "warn_depth", 25.0)
    critical_depth_threshold = _resolve_threshold(args.critical_depth_threshold, policy, "critical_depth", 100.0)
    warn_dead_rate_threshold = _resolve_threshold(args.warn_dead_rate_threshold, policy, "warn_dead_rate", 0.2)
    critical_dead_rate_threshold = _resolve_threshold(args.critical_dead_rate_threshold, policy, "critical_dead_rate", 0.4)
    retry_age_warn_seconds = _resolve_threshold(None, policy, "retry_age_p95_warn_seconds", 600.0)

    if not snapshot_path.exists():
        payload = {
            "artifact_kind": "notification-outbox-self-heal",
            "schema_version": "v1",
            "result": "skipped" if args.allow_missing_snapshot else "fail",
            "reasons": ["snapshot_missing"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "meta": {"snapshot": str(snapshot_path), "policy": str(policy_path)},
            "actions": [],
        }
        _write(output_path, payload)
        print(f"[outbox-self-heal] result={payload['result']} reasons=snapshot_missing output={output_path}")
        return 0 if args.allow_missing_snapshot else 1

    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    outbox = payload.get("outbox") if isinstance(payload, dict) else {}
    if not isinstance(outbox, dict):
        outbox = {}

    depth = _safe_number(outbox.get("depth"))
    dead_rate = _safe_number(outbox.get("dead_letter_rate"))
    stale_processing = _safe_number(outbox.get("stale_processing_count")) or 0.0
    retry_age_p95 = _safe_number(outbox.get("retry_age_p95_seconds")) or 0.0
    actions: list[dict[str, str]] = []
    reasons: list[str] = []

    if stale_processing > 0:
        if _is_action_enabled(policy, "enable_reclaim_stale_processing"):
            actions.append({"action": "reclaim_stale_processing", "priority": "high"})
            reasons.append("stale_processing_detected")

    if depth is not None and depth >= critical_depth_threshold:
        if _is_action_enabled(policy, "enable_pause_noncritical_notifications"):
            actions.append({"action": "pause_noncritical_notifications", "priority": "critical"})
        if _is_action_enabled(policy, "enable_run_outbox_recovery_apply"):
            actions.append({"action": "run_outbox_recovery_apply", "priority": "critical"})
        reasons.append("outbox_depth_critical")
    elif depth is not None and depth >= warn_depth_threshold:
        actions.append({"action": "run_outbox_recovery_dry_run", "priority": "high"})
        reasons.append("outbox_depth_warn")

    if dead_rate is not None and dead_rate >= critical_dead_rate_threshold:
        if _is_action_enabled(policy, "enable_run_dead_letter_replay"):
            actions.append({"action": "run_dead_letter_replay", "priority": "critical"})
        reasons.append("dead_letter_rate_critical")
    elif dead_rate is not None and dead_rate >= warn_dead_rate_threshold:
        if _is_action_enabled(policy, "enable_run_dead_letter_audit"):
            actions.append({"action": "run_dead_letter_audit", "priority": "high"})
        reasons.append("dead_letter_rate_warn")

    if retry_age_p95 >= retry_age_warn_seconds:
        if _is_action_enabled(policy, "enable_increase_dispatch_workers_temporarily"):
            actions.append({"action": "increase_dispatch_workers_temporarily", "priority": "high"})
        reasons.append("retry_age_p95_high")

    result = "pass" if not reasons else "degraded"
    summary = {
        "artifact_kind": "notification-outbox-self-heal",
        "schema_version": "v1",
        "result": result,
        "reasons": sorted(set(reasons)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "snapshot": str(snapshot_path),
            "depth": depth,
            "dead_letter_rate": dead_rate,
            "stale_processing_count": stale_processing,
            "retry_age_p95_seconds": retry_age_p95,
            "policy": str(policy_path),
            "warn_depth_threshold": warn_depth_threshold,
            "critical_depth_threshold": critical_depth_threshold,
            "warn_dead_rate_threshold": warn_dead_rate_threshold,
            "critical_dead_rate_threshold": critical_dead_rate_threshold,
        },
        "actions": actions,
        "apply_safe_actions": bool(args.apply_safe_actions),
        "applied_actions": [],
    }

    if args.apply_safe_actions and actions:
        apply_errors: list[str] = []
        try:
            from app.services import notification_outbox as outbox_service
        except Exception as exc:  # pragma: no cover - defensive import fallback
            apply_errors.append(f"service_import_failed:{type(exc).__name__}")
            outbox_service = None

        for item in actions:
            action_name = str(item.get("action") or "")
            if not outbox_service:
                break
            try:
                if action_name == "reclaim_stale_processing" and hasattr(
                    outbox_service, "reclaim_stale_processing_notifications"
                ):
                    reclaimed = outbox_service.reclaim_stale_processing_notifications()
                    summary["applied_actions"].append(
                        {"action": action_name, "result": "applied", "reclaimed": int(reclaimed)}
                    )
                elif action_name in {"run_dead_letter_replay", "run_outbox_recovery_apply"} and hasattr(
                    outbox_service, "replay_dead_notification_outbox"
                ):
                    replay_summary = outbox_service.replay_dead_notification_outbox(
                        limit=max(1, int(args.recovery_replay_limit)),
                        reset_attempt_count=False,
                    )
                    summary["applied_actions"].append(
                        {
                            "action": action_name,
                            "result": "applied",
                            "replayed": int(replay_summary.get("replayed", 0)),
                            "errors": int(replay_summary.get("errors", 0)),
                        }
                    )
                elif action_name == "run_dead_letter_audit":
                    summary["applied_actions"].append({"action": action_name, "result": "skipped_readonly"})
                else:
                    summary["applied_actions"].append({"action": action_name, "result": "not_safe_to_apply"})
            except Exception as exc:  # pragma: no cover - defensive
                apply_errors.append(f"{action_name}:{type(exc).__name__}")
                summary["applied_actions"].append({"action": action_name, "result": "failed"})

        if apply_errors:
            summary["result"] = "degraded"
            merged = sorted(set(summary["reasons"] + ["safe_action_apply_failed"]))
            summary["reasons"] = merged
            summary["apply_errors"] = apply_errors

    _write(output_path, summary)
    print(
        "[outbox-self-heal] result={result} reasons={reasons} actions={actions} output={output}".format(
            result=result,
            reasons="none" if not reasons else ",".join(sorted(set(reasons))),
            actions=len(actions),
            output=output_path,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
