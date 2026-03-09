from __future__ import annotations

import json
from pathlib import Path

from scripts.run_unit_economics_report import generate_report, main


def test_generate_report_computes_blended_cost() -> None:
    payload = generate_report(active_couples=20)
    assert payload["artifact_kind"] == "unit-economics-report"
    assert payload["active_couples"] == 20
    assert payload["computed"]["total_cost_month"] >= payload["computed"]["fixed_cost_month"]
    assert payload["computed"]["blended_cost_per_couple_month"] > 0


def test_main_writes_report_with_override(tmp_path: Path) -> None:
    output = tmp_path / "unit-economics-report.json"
    exit_code = main(["--active-couples", "7", "--output", str(output)])
    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["active_couples"] == 7
    assert payload["active_couples_source"] == "override"


def test_main_exits_1_on_warning_when_fail_on_warning(tmp_path: Path) -> None:
    """FIN-01: --fail-on-warning triggers exit 1 when health=warning for alert routing."""
    output = tmp_path / "unit-economics-report.json"
    # active_couples=0 yields high cost_per_couple -> health=warning
    exit_code = main(
        ["--active-couples", "0", "--output", str(output), "--fail-on-warning"]
    )
    assert exit_code == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["health"] == "warning"
