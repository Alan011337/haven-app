#!/usr/bin/env python3
"""Policy-as-code gate for prompt abuse policy contract."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.prompt_abuse import iter_prompt_abuse_pattern_ids  # noqa: E402

POLICY_PATH = REPO_ROOT / "docs" / "security" / "prompt-abuse-policy.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "prompt-abuse-policy"
ALLOWED_SEVERITY = {"low", "medium", "high", "critical"}


@dataclass(frozen=True)
class PromptAbusePolicyViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_prompt_abuse_policy_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[PromptAbusePolicyViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[PromptAbusePolicyViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            PromptAbusePolicyViolation("invalid_schema_version", f"schema_version must be `{SCHEMA_VERSION}`.")
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            PromptAbusePolicyViolation("invalid_artifact_kind", f"artifact_kind must be `{ARTIFACT_KIND}`.")
        )
    if policy.get("mode") != "block_and_fallback":
        violations.append(
            PromptAbusePolicyViolation("invalid_mode", "mode must be `block_and_fallback`.")
        )

    patterns = policy.get("patterns")
    pattern_ids: set[str] = set()
    if not isinstance(patterns, list) or not patterns:
        violations.append(PromptAbusePolicyViolation("invalid_patterns", "patterns must be non-empty list."))
        patterns = []
    for idx, item in enumerate(patterns):
        if not isinstance(item, dict):
            violations.append(
                PromptAbusePolicyViolation("invalid_pattern_entry", f"patterns[{idx}] must be object.")
            )
            continue
        pattern_id = str(item.get("id", "")).strip()
        if not pattern_id:
            violations.append(
                PromptAbusePolicyViolation("missing_pattern_id", f"patterns[{idx}].id required.")
            )
            continue
        if pattern_id in pattern_ids:
            violations.append(
                PromptAbusePolicyViolation("duplicate_pattern_id", f"duplicate pattern id `{pattern_id}`.")
            )
        pattern_ids.add(pattern_id)
        severity = str(item.get("severity", "")).strip()
        if severity not in ALLOWED_SEVERITY:
            violations.append(
                PromptAbusePolicyViolation(
                    "invalid_pattern_severity",
                    f"patterns[{idx}].severity `{severity}` must be one of {sorted(ALLOWED_SEVERITY)}.",
                )
            )
        if not str(item.get("description", "")).strip():
            violations.append(
                PromptAbusePolicyViolation("missing_pattern_description", f"patterns[{idx}].description required.")
            )

    runtime_ids = set(iter_prompt_abuse_pattern_ids())
    missing_runtime = sorted(pattern_ids - runtime_ids)
    if missing_runtime:
        violations.append(
            PromptAbusePolicyViolation(
                "pattern_not_implemented",
                f"policy patterns missing in runtime service: {', '.join(missing_runtime)}",
            )
        )

    enforcement = policy.get("enforcement")
    if not isinstance(enforcement, dict):
        violations.append(
            PromptAbusePolicyViolation("invalid_enforcement", "enforcement must be object.")
        )
    else:
        for key in ("service", "entrypoint"):
            path = enforcement.get(key)
            if not isinstance(path, str) or not path.strip():
                violations.append(
                    PromptAbusePolicyViolation("invalid_enforcement_path", f"enforcement.{key} must be path.")
                )
                continue
            if not (REPO_ROOT / path).exists():
                violations.append(
                    PromptAbusePolicyViolation(
                        "missing_enforcement_file",
                        f"enforcement.{key} file not found: {path}",
                    )
                )

    tests = policy.get("tests")
    if not isinstance(tests, list) or not tests:
        violations.append(PromptAbusePolicyViolation("invalid_tests", "tests must be non-empty list."))
    else:
        for idx, path in enumerate(tests):
            if not isinstance(path, str) or not path.strip():
                violations.append(
                    PromptAbusePolicyViolation("invalid_test_path", f"tests[{idx}] must be path string.")
                )
                continue
            if not (REPO_ROOT / path).exists():
                violations.append(
                    PromptAbusePolicyViolation("missing_test_file", f"tests[{idx}] file not found: {path}")
                )

    return violations


def run_policy_check() -> int:
    violations = collect_prompt_abuse_policy_contract_violations()
    if not violations:
        print("[prompt-abuse-policy-contract] ok: prompt abuse policy contract satisfied")
        return 0
    print("[prompt-abuse-policy-contract] failed:", file=sys.stderr)
    for v in violations:
        print(f"  - reason={v.reason} details={v.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
