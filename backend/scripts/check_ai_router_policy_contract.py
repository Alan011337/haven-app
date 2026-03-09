#!/usr/bin/env python3
"""Policy-as-code gate for AI router contract (P1-I)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

POLICY_PATH = REPO_ROOT / "docs" / "security" / "ai-router-policy.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "ai-router-policy"
REQUIRED_PROVIDERS = {"openai", "gemini"}
REQUIRED_ROUTER_TASKS = {"l1_classify_extract", "l2_deep_reasoning"}
ALLOWED_BACKOFF_JITTER = {"none", "full"}
ALLOWED_IDEMPOTENCY_MISMATCH_ACTIONS = {"bypass_and_continue", "reject"}
ALLOWED_RESULT_CACHE_MODES = {"success_only", "success_and_failure"}
ALLOWED_DUPLICATE_EXIT_ACTIONS = {"graceful_fallback", "failover_next"}


@dataclass(frozen=True)
class AIRouterPolicyViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def collect_ai_router_policy_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[AIRouterPolicyViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[AIRouterPolicyViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            AIRouterPolicyViolation(
                "invalid_schema_version",
                f"schema_version must be `{SCHEMA_VERSION}`.",
            )
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            AIRouterPolicyViolation(
                "invalid_artifact_kind",
                f"artifact_kind must be `{ARTIFACT_KIND}`.",
            )
        )

    supported_providers = policy.get("supported_providers")
    if not isinstance(supported_providers, list) or not supported_providers:
        violations.append(
            AIRouterPolicyViolation(
                "invalid_supported_providers",
                "supported_providers must be non-empty list.",
            )
        )
    else:
        provider_set = {str(item).strip().lower() for item in supported_providers}
        missing = sorted(REQUIRED_PROVIDERS - provider_set)
        if missing:
            violations.append(
                AIRouterPolicyViolation(
                    "missing_supported_provider",
                    "missing providers: " + ", ".join(missing),
                )
            )

    routing = policy.get("routing")
    if not isinstance(routing, dict):
        violations.append(
            AIRouterPolicyViolation(
                "invalid_routing",
                "routing must be object.",
            )
        )
    else:
        if routing.get("default_primary_provider") != "openai":
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_default_primary_provider",
                    "routing.default_primary_provider must be `openai`.",
                )
            )
        if routing.get("allow_fallback") is not True:
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_allow_fallback",
                    "routing.allow_fallback must be true.",
                )
            )
        if routing.get("fallback_mode") != "primary_then_fallback":
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_fallback_mode",
                    "routing.fallback_mode must be `primary_then_fallback`.",
                )
            )
        if routing.get("degradation_policy") != "fallback_to_openai_when_provider_unavailable":
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_degradation_policy",
                    "routing.degradation_policy must be "
                    "`fallback_to_openai_when_provider_unavailable`.",
                )
            )
        analysis_task = routing.get("analysis_task")
        if not isinstance(analysis_task, str) or analysis_task not in REQUIRED_ROUTER_TASKS:
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_analysis_task",
                    "routing.analysis_task must be one of l1_classify_extract|l2_deep_reasoning.",
                )
            )

        task_policy = routing.get("task_policy")
        if not isinstance(task_policy, dict):
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_task_policy",
                    "routing.task_policy must be object.",
                )
            )
        else:
            for task_name in sorted(REQUIRED_ROUTER_TASKS):
                task_entry = task_policy.get(task_name)
                if not isinstance(task_entry, dict):
                    violations.append(
                        AIRouterPolicyViolation(
                            "missing_task_policy_entry",
                            f"routing.task_policy.{task_name} must be object.",
                        )
                    )
                    continue
                primary_provider = str(task_entry.get("primary_provider", "")).strip().lower()
                fallback_provider = str(task_entry.get("fallback_provider", "")).strip().lower()
                if primary_provider not in REQUIRED_PROVIDERS:
                    violations.append(
                        AIRouterPolicyViolation(
                            "invalid_task_policy_primary_provider",
                            f"routing.task_policy.{task_name}.primary_provider must be openai|gemini.",
                        )
                    )
                if fallback_provider not in REQUIRED_PROVIDERS:
                    violations.append(
                        AIRouterPolicyViolation(
                            "invalid_task_policy_fallback_provider",
                            f"routing.task_policy.{task_name}.fallback_provider must be openai|gemini.",
                        )
                    )

    budget_guardrails = policy.get("budget_guardrails")
    if not isinstance(budget_guardrails, dict):
        violations.append(
            AIRouterPolicyViolation(
                "invalid_budget_guardrails",
                "budget_guardrails must be object.",
            )
        )
    else:
        if budget_guardrails.get("cost_guard_mode") not in {"observe_only", "enforced"}:
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_cost_guard_mode",
                    "budget_guardrails.cost_guard_mode must be observe_only|enforced.",
                )
            )
        if not isinstance(budget_guardrails.get("token_budget_enforced"), bool):
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_token_budget_enforced",
                    "budget_guardrails.token_budget_enforced must be boolean.",
                )
            )

    runtime_policy = policy.get("runtime_policy")
    if not isinstance(runtime_policy, dict):
        violations.append(
            AIRouterPolicyViolation(
                "invalid_runtime_policy",
                "runtime_policy must be object.",
            )
        )
    else:
        if not isinstance(runtime_policy.get("free_tier_first_enabled"), bool):
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_free_tier_first_enabled",
                    "runtime_policy.free_tier_first_enabled must be boolean.",
                )
            )

        idempotency = runtime_policy.get("idempotency")
        if not isinstance(idempotency, dict):
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_runtime_idempotency",
                    "runtime_policy.idempotency must be object.",
                )
            )
        else:
            mismatch_action = str(idempotency.get("mismatch_action", "")).strip().lower()
            if mismatch_action not in ALLOWED_IDEMPOTENCY_MISMATCH_ACTIONS:
                violations.append(
                    AIRouterPolicyViolation(
                        "invalid_idempotency_mismatch_action",
                        "runtime_policy.idempotency.mismatch_action must be bypass_and_continue|reject.",
                    )
                )
            precedence = idempotency.get("status_precedence")
            if not isinstance(precedence, list) or precedence[:2] != [
                "inflight_conflict_409",
                "fingerprint_mismatch_422",
            ]:
                violations.append(
                    AIRouterPolicyViolation(
                        "invalid_idempotency_status_precedence",
                        "runtime_policy.idempotency.status_precedence must start with inflight_conflict_409,fingerprint_mismatch_422.",
                    )
                )

        retry = runtime_policy.get("retry")
        if not isinstance(retry, dict):
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_runtime_retry",
                    "runtime_policy.retry must be object.",
                )
            )
        else:
            for key in ("max_attempts_per_profile", "max_total_attempts", "max_elapsed_ms"):
                value = retry.get(key)
                if not isinstance(value, int) or value <= 0:
                    violations.append(
                        AIRouterPolicyViolation(
                            "invalid_retry_budget",
                            f"runtime_policy.retry.{key} must be positive integer.",
                        )
                    )
            threshold = retry.get("rate_limit_failover_threshold_seconds")
            if not isinstance(threshold, (int, float)) or float(threshold) < 0:
                violations.append(
                    AIRouterPolicyViolation(
                        "invalid_rate_limit_failover_threshold",
                        "runtime_policy.retry.rate_limit_failover_threshold_seconds must be >= 0.",
                    )
                )
            backoff = retry.get("backoff")
            if not isinstance(backoff, dict):
                violations.append(
                    AIRouterPolicyViolation(
                        "invalid_retry_backoff",
                        "runtime_policy.retry.backoff must be object.",
                    )
                )
            else:
                for key in ("base_ms", "max_ms"):
                    value = backoff.get(key)
                    if not isinstance(value, int) or value < 0:
                        violations.append(
                            AIRouterPolicyViolation(
                                "invalid_retry_backoff_budget",
                                f"runtime_policy.retry.backoff.{key} must be non-negative integer.",
                            )
                        )
                jitter = str(backoff.get("jitter", "")).strip().lower()
                if jitter not in ALLOWED_BACKOFF_JITTER:
                    violations.append(
                        AIRouterPolicyViolation(
                            "invalid_retry_backoff_jitter",
                            "runtime_policy.retry.backoff.jitter must be none|full.",
                        )
                    )

        result_cache = runtime_policy.get("result_cache")
        if not isinstance(result_cache, dict):
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_runtime_result_cache",
                    "runtime_policy.result_cache must be object.",
                )
            )
        else:
            if not isinstance(result_cache.get("enabled"), bool):
                violations.append(
                    AIRouterPolicyViolation(
                        "invalid_result_cache_enabled",
                        "runtime_policy.result_cache.enabled must be boolean.",
                    )
                )
            mode = str(result_cache.get("mode", "")).strip().lower()
            if mode not in ALLOWED_RESULT_CACHE_MODES:
                violations.append(
                    AIRouterPolicyViolation(
                        "invalid_result_cache_mode",
                        "runtime_policy.result_cache.mode must be success_only|success_and_failure.",
                    )
                )
            ttl_map = result_cache.get("ttl_success_s_by_request_class")
            if not isinstance(ttl_map, dict) or not ttl_map:
                violations.append(
                    AIRouterPolicyViolation(
                        "invalid_result_cache_success_ttl_map",
                        "runtime_policy.result_cache.ttl_success_s_by_request_class must be non-empty object.",
                    )
                )
            failure_ttl = result_cache.get("ttl_failure_s")
            if not isinstance(failure_ttl, int) or failure_ttl <= 0:
                violations.append(
                    AIRouterPolicyViolation(
                        "invalid_result_cache_failure_ttl",
                        "runtime_policy.result_cache.ttl_failure_s must be positive integer.",
                    )
                )

        duplicate = runtime_policy.get("duplicate_handling")
        if not isinstance(duplicate, dict):
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_runtime_duplicate_handling",
                    "runtime_policy.duplicate_handling must be object.",
                )
            )
        else:
            for key in ("poll_interval_ms", "poll_jitter_ms_max", "poll_max_consecutive_miss", "fast_yield_remaining_budget_ms"):
                value = duplicate.get(key)
                if not isinstance(value, int) or value < 0:
                    violations.append(
                        AIRouterPolicyViolation(
                            "invalid_duplicate_handling_budget",
                            f"runtime_policy.duplicate_handling.{key} must be non-negative integer.",
                        )
                    )
            exit_action = str(duplicate.get("exit_action", "")).strip().lower()
            if exit_action not in ALLOWED_DUPLICATE_EXIT_ACTIONS:
                violations.append(
                    AIRouterPolicyViolation(
                        "invalid_duplicate_exit_action",
                        "runtime_policy.duplicate_handling.exit_action must be graceful_fallback|failover_next.",
                    )
                )

        schema_cooldown = runtime_policy.get("schema_cooldown")
        if not isinstance(schema_cooldown, dict):
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_runtime_schema_cooldown",
                    "runtime_policy.schema_cooldown must be object.",
                )
            )
        else:
            for key in ("failure_threshold", "window_seconds", "cooldown_seconds"):
                value = schema_cooldown.get(key)
                if not isinstance(value, int) or value <= 0:
                    violations.append(
                        AIRouterPolicyViolation(
                            "invalid_schema_cooldown_budget",
                            f"runtime_policy.schema_cooldown.{key} must be positive integer.",
                        )
                    )

        degraded_mode = runtime_policy.get("degraded_mode")
        if not isinstance(degraded_mode, dict):
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_runtime_degraded_mode",
                    "runtime_policy.degraded_mode must be object.",
                )
            )
        else:
            for key in (
                "disable_result_cache",
                "disable_inflight_poll",
                "disable_cooldown_enforce",
            ):
                if not isinstance(degraded_mode.get(key), bool):
                    violations.append(
                        AIRouterPolicyViolation(
                            "invalid_degraded_mode_flag",
                            f"runtime_policy.degraded_mode.{key} must be boolean.",
                        )
                    )
            for key in ("force_max_total_attempts", "force_backoff_base_ms", "force_backoff_max_ms"):
                value = degraded_mode.get(key)
                if not isinstance(value, int) or value < 0:
                    violations.append(
                        AIRouterPolicyViolation(
                            "invalid_degraded_mode_budget",
                            f"runtime_policy.degraded_mode.{key} must be non-negative integer.",
                        )
                    )

        metrics = runtime_policy.get("metrics")
        if not isinstance(metrics, dict):
            violations.append(
                AIRouterPolicyViolation(
                    "invalid_runtime_metrics",
                    "runtime_policy.metrics must be object.",
                )
            )
        else:
            for key in ("enforce_enum_labels", "forbid_dynamic_unknown_mapping"):
                if not isinstance(metrics.get(key), bool):
                    violations.append(
                        AIRouterPolicyViolation(
                            "invalid_runtime_metrics_flag",
                            f"runtime_policy.metrics.{key} must be boolean.",
                        )
                    )
            unknown_bucket = str(metrics.get("unknown_bucket", "")).strip().lower()
            if unknown_bucket != "unknown":
                violations.append(
                    AIRouterPolicyViolation(
                        "invalid_runtime_metrics_unknown_bucket",
                        "runtime_policy.metrics.unknown_bucket must be `unknown`.",
                    )
                )

    references = policy.get("references")
    if not isinstance(references, dict) or not references:
        violations.append(
            AIRouterPolicyViolation("invalid_references", "references must be non-empty object.")
        )
    else:
        for key, rel_path in references.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(
                    AIRouterPolicyViolation(
                        "invalid_reference_path",
                        f"references.{key} must be path string.",
                    )
                )
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    AIRouterPolicyViolation(
                        "missing_reference_file",
                        f"references.{key} not found: {rel_path}",
                    )
                )

        router_service = references.get("router_service")
        if isinstance(router_service, str) and router_service.strip():
            router_text = _read_text(REPO_ROOT / router_service)
            for marker in (
                "SUPPORTED_PROVIDERS",
                "SUPPORTED_ROUTER_TASKS",
                "SUPPORTED_PROFILES",
                "AIRouterRequestContext",
                "build_provider_chain",
                "normalize_router_task",
                "select_analysis_route",
                "select_task_route",
                "build_input_fingerprint",
                "normalize_idempotency_key",
                "AIProviderAdapter",
                "run_provider_adapters",
                "ai_router_runtime_metrics",
                "build_ai_router_runtime_payload",
            ):
                if marker not in router_text:
                    violations.append(
                        AIRouterPolicyViolation(
                            "missing_router_service_marker",
                            f"router service missing marker `{marker}`.",
                        )
                    )

        analysis_service = references.get("analysis_service")
        if isinstance(analysis_service, str) and analysis_service.strip():
            analysis_text = _read_text(REPO_ROOT / analysis_service)
            if "select_task_route" not in analysis_text:
                violations.append(
                    AIRouterPolicyViolation(
                        "missing_analysis_router_integration",
                        "analysis service must call `select_task_route`.",
                    )
                )
            if "run_provider_adapters" not in analysis_text:
                violations.append(
                    AIRouterPolicyViolation(
                        "missing_runtime_fallback_integration",
                        "analysis service must call `run_provider_adapters`.",
                    )
                )

    return violations


def run_policy_check() -> int:
    violations = collect_ai_router_policy_contract_violations()
    if not violations:
        print("[ai-router-policy-contract] ok: ai router policy contract satisfied")
        return 0

    print("[ai-router-policy-contract] failed:", file=sys.stderr)
    for violation in violations:
        print(f"  - reason={violation.reason} details={violation.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
