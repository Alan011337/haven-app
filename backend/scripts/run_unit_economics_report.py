#!/usr/bin/env python3
"""FIN-01: Unit economics monitor.

Generates a periodic report of per-active-couple cost metrics.
Designed to run as a scheduled job (cron / CI workflow).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_ROOT = REPO_ROOT / "docs"

# Cost model assumptions (override with environment variables)
COST_MODEL = {
    "openai_cost_per_1k_tokens": 0.002,
    "avg_tokens_per_journal_analysis": 800,
    "avg_journals_per_couple_per_month": 30,
    "supabase_cost_per_gb_month": 0.021,
    "avg_storage_per_couple_gb": 0.05,
    "push_notification_cost_per_1k": 0.0,  # free tier
    "infra_fixed_cost_per_month_usd": 25.0,
}


def _count_active_couples_from_db() -> int:
    """Count active bidirectional couples from users table."""
    backend_root = REPO_ROOT / "backend"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    from sqlmodel import Session, select  # local import for script portability

    from app.db.session import engine
    from app.models.user import User

    with Session(engine) as session:
        rows = session.exec(
            select(User.id, User.partner_id).where(
                User.deleted_at.is_(None),
                User.partner_id.is_not(None),
            )
        ).all()

    pair_keys: set[tuple[str, str]] = set()
    partner_map = {str(user_id): str(partner_id) for user_id, partner_id in rows if partner_id}
    for user_id, partner_id in rows:
        if not partner_id:
            continue
        uid = str(user_id)
        pid = str(partner_id)
        # only count valid bidirectional bindings
        if partner_map.get(pid) != uid:
            continue
        key = tuple(sorted((uid, pid)))
        pair_keys.add(key)
    return len(pair_keys)


def _compute_variable_cost_per_couple() -> float:
    ai_cost = (
        COST_MODEL["openai_cost_per_1k_tokens"]
        * COST_MODEL["avg_tokens_per_journal_analysis"]
        / 1000
        * COST_MODEL["avg_journals_per_couple_per_month"]
    )
    storage_cost = (
        COST_MODEL["supabase_cost_per_gb_month"]
        * COST_MODEL["avg_storage_per_couple_gb"]
    )
    return round(ai_cost + storage_cost, 4)


def generate_report(*, active_couples: int = 0) -> dict:
    """Generate unit economics report."""
    variable_per_couple = _compute_variable_cost_per_couple()
    total_variable = round(variable_per_couple * active_couples, 2)
    total_cost = round(COST_MODEL["infra_fixed_cost_per_month_usd"] + total_variable, 2)
    cost_per_couple = round(total_cost / max(1, active_couples), 4)

    return {
        "artifact_kind": "unit-economics-report",
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_couples": active_couples,
        "cost_model": COST_MODEL,
        "computed": {
            "variable_cost_per_couple_month": variable_per_couple,
            "total_variable_cost_month": total_variable,
            "fixed_cost_month": COST_MODEL["infra_fixed_cost_per_month_usd"],
            "total_cost_month": total_cost,
            "blended_cost_per_couple_month": cost_per_couple,
        },
        "health": "ok" if cost_per_couple < 2.0 else "warning",
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate FIN-01 unit economics report.")
    parser.add_argument(
        "--active-couples",
        type=int,
        default=None,
        help="Optional override for active couples count (default: auto query from DB).",
    )
    parser.add_argument(
        "--output",
        default=str(DOCS_ROOT / "security" / "unit-economics-report.json"),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit 1 when report health is 'warning' (for CI alert routing).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    active_couples = (
        max(0, int(args.active_couples))
        if args.active_couples is not None
        else _count_active_couples_from_db()
    )
    report = generate_report(active_couples=active_couples)
    report["active_couples_source"] = "override" if args.active_couples is not None else "database"
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"FIN-01 unit economics report written to {output_path}")
    print(json.dumps(report, indent=2))
    if args.fail_on_warning and report.get("health") == "warning":
        print("FIN-01 health=warning; exiting 1 for alert routing")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
