#!/usr/bin/env python3
"""Policy-as-code gate for CUJ synthetic monitoring contract."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

SYNTHETIC_SCRIPT_PATH = REPO_ROOT / "scripts" / "synthetics" / "run_cuj_synthetics.py"
SYNTHETIC_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cuj-synthetics.yml"
SYNTHETIC_DOC_PATH = REPO_ROOT / "docs" / "sre" / "synthetic-cuj.md"
ALERTS_DOC_PATH = REPO_ROOT / "docs" / "sre" / "alerts.md"

REQUIRED_SYNTHETIC_SCRIPT_FRAGMENTS: tuple[str, ...] = (
    "--summary-path",
    "classify_synthetic_failure(",
    '"failure_class"',
    "cuj_slo_gate",
)
REQUIRED_SYNTHETIC_WORKFLOW_FRAGMENTS: tuple[str, ...] = (
    "--summary-path /tmp/cuj-synthetics-summary.json",
    "name: CUJ synthetic summary",
    "failure_class",
    "Failed stages",
    "docs/sre/evidence/cuj-synthetic-*.md",
    "docs/sre/evidence/cuj-synthetic-*.json",
)
REQUIRED_SYNTHETIC_DOC_FRAGMENTS: tuple[str, ...] = (
    "failure_class",
    "failed_stages",
    "SLO checks consume `/health/slo` statuses: `ws`, `ws_burn_rate`, `cuj`",
)
REQUIRED_ALERTS_DOC_FRAGMENTS: tuple[str, ...] = (
    "Failure Class Routing (Synthetic CUJ)",
    "`cuj_slo_degraded`",
    "`journal_latency_regression`",
)


@dataclass(frozen=True)
class CujSyntheticContractViolation:
    reason: str
    details: str


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _check_required_fragments(
    *,
    content: str,
    required_fragments: tuple[str, ...],
    reason: str,
    label: str,
) -> list[CujSyntheticContractViolation]:
    violations: list[CujSyntheticContractViolation] = []
    for fragment in required_fragments:
        if fragment not in content:
            violations.append(
                CujSyntheticContractViolation(
                    reason=reason,
                    details=f"{label} missing required fragment: {fragment}",
                )
            )
    return violations


def collect_cuj_synthetic_contract_violations(
    *,
    synthetic_script_text: str | None = None,
    workflow_text: str | None = None,
    synthetic_doc_text: str | None = None,
    alerts_doc_text: str | None = None,
) -> list[CujSyntheticContractViolation]:
    violations: list[CujSyntheticContractViolation] = []

    if synthetic_script_text is None:
        if not SYNTHETIC_SCRIPT_PATH.exists():
            violations.append(
                CujSyntheticContractViolation(
                    reason="missing_synthetic_script",
                    details=f"{SYNTHETIC_SCRIPT_PATH} not found.",
                )
            )
            synthetic_script_text = ""
        else:
            synthetic_script_text = _load_text(SYNTHETIC_SCRIPT_PATH)
    violations.extend(
        _check_required_fragments(
            content=synthetic_script_text,
            required_fragments=REQUIRED_SYNTHETIC_SCRIPT_FRAGMENTS,
            reason="missing_synthetic_script_fragment",
            label="synthetic script",
        )
    )

    if workflow_text is None:
        if not SYNTHETIC_WORKFLOW_PATH.exists():
            violations.append(
                CujSyntheticContractViolation(
                    reason="missing_synthetic_workflow",
                    details=f"{SYNTHETIC_WORKFLOW_PATH} not found.",
                )
            )
            workflow_text = ""
        else:
            workflow_text = _load_text(SYNTHETIC_WORKFLOW_PATH)
    violations.extend(
        _check_required_fragments(
            content=workflow_text,
            required_fragments=REQUIRED_SYNTHETIC_WORKFLOW_FRAGMENTS,
            reason="missing_synthetic_workflow_fragment",
            label="synthetic workflow",
        )
    )

    if synthetic_doc_text is None:
        if not SYNTHETIC_DOC_PATH.exists():
            violations.append(
                CujSyntheticContractViolation(
                    reason="missing_synthetic_doc",
                    details=f"{SYNTHETIC_DOC_PATH} not found.",
                )
            )
            synthetic_doc_text = ""
        else:
            synthetic_doc_text = _load_text(SYNTHETIC_DOC_PATH)
    violations.extend(
        _check_required_fragments(
            content=synthetic_doc_text,
            required_fragments=REQUIRED_SYNTHETIC_DOC_FRAGMENTS,
            reason="missing_synthetic_doc_fragment",
            label="synthetic doc",
        )
    )

    if alerts_doc_text is None:
        if not ALERTS_DOC_PATH.exists():
            violations.append(
                CujSyntheticContractViolation(
                    reason="missing_alerts_doc",
                    details=f"{ALERTS_DOC_PATH} not found.",
                )
            )
            alerts_doc_text = ""
        else:
            alerts_doc_text = _load_text(ALERTS_DOC_PATH)
    violations.extend(
        _check_required_fragments(
            content=alerts_doc_text,
            required_fragments=REQUIRED_ALERTS_DOC_FRAGMENTS,
            reason="missing_alerts_doc_fragment",
            label="alerts doc",
        )
    )

    return violations


def run_policy_check() -> int:
    violations = collect_cuj_synthetic_contract_violations()
    if not violations:
        print("[cuj-synthetic-contract] ok: cuj synthetic contract satisfied")
        return 0

    print("[cuj-synthetic-contract] failed:", file=sys.stderr)
    for violation in violations:
        print(
            f"  - reason={violation.reason} details={violation.details}",
            file=sys.stderr,
        )
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
