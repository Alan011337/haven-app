#!/usr/bin/env python3
"""Export EXPLAIN-plan baseline for memory timeline cursor queries."""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.services.memory_archive import (  # noqa: E402
    _build_card_session_timeline_stmt,
    _build_journal_timeline_stmt,
)


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def _compile_sql(statement, engine) -> str:
    return str(
        statement.compile(
            dialect=engine.dialect,
            compile_kwargs={"literal_binds": True},
        )
    )


def _explain_query_plan(*, session: Session, sql: str) -> list[str]:
    rows = list(session.exec(text(f"EXPLAIN QUERY PLAN {sql}")).all())
    return [str(row[-1]) for row in rows]


def _index_detected(plan_details: list[str]) -> bool:
    combined = " ".join(plan_details).upper()
    return "INDEX" in combined


def _uses_date_function(sql: str) -> bool:
    return bool(re.search(r"\bDATE\s*\(", sql, flags=re.IGNORECASE))


def _has_forbidden_full_scan(plan_details: list[str], *, table_name: str) -> bool:
    table = table_name.upper()
    for raw in plan_details:
        detail = str(raw).upper()
        # Accept indexed scans, fail on plain table scan.
        if f"SCAN {table}" in detail and "USING INDEX" not in detail and "USING COVERING INDEX" not in detail:
            return True
    return False


def build_baseline_payload() -> dict[str, Any]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    user_id = uuid.UUID("00000000-0000-0000-0000-000000000111")
    before = datetime(2026, 3, 1, tzinfo=timezone.utc)
    from_date = date(2026, 2, 1)
    to_date = date(2026, 3, 2)

    with Session(engine) as session:
        session.exec(
            text(
                "CREATE INDEX IF NOT EXISTS idx_journals_user_created_id "
                "ON journals (user_id, created_at DESC, id DESC)"
            )
        )
        session.exec(
            text(
                "CREATE INDEX IF NOT EXISTS idx_card_sessions_creator_created_id "
                "ON card_sessions (creator_id, created_at DESC, id DESC)"
            )
        )
        session.commit()

        journal_stmt = _build_journal_timeline_stmt(
            user_ids=[user_id],
            before=before,
            cursor_last_id=None,
            from_date=from_date,
            to_date=to_date,
            fetch_n=20,
        )
        card_stmt = _build_card_session_timeline_stmt(
            clauses=[
                CardSession.mode == CardSessionMode.DECK,
                CardSession.status == CardSessionStatus.COMPLETED,
                CardSession.deleted_at.is_(None),
                CardSession.creator_id == user_id,
            ],
            before=before,
            cursor_last_id=None,
            from_date=from_date,
            to_date=to_date,
            fetch_n=20,
        )

        journal_sql = _compile_sql(journal_stmt, engine)
        card_sql = _compile_sql(card_stmt, engine)
        journal_plan = _explain_query_plan(session=session, sql=journal_sql)
        card_plan = _explain_query_plan(session=session, sql=card_sql)

    engine.dispose()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dialect": "sqlite",
        "timeline_query_plan": {
            "journal": {
                "sql": journal_sql,
                "plan_details": journal_plan,
                "index_detected": _index_detected(journal_plan),
                "uses_date_function": _uses_date_function(journal_sql),
                "full_scan_detected": _has_forbidden_full_scan(journal_plan, table_name="journals"),
            },
            "card_session": {
                "sql": card_sql,
                "plan_details": card_plan,
                "index_detected": _index_detected(card_plan),
                "uses_date_function": _uses_date_function(card_sql),
                "full_scan_detected": _has_forbidden_full_scan(card_plan, table_name="card_sessions"),
            },
        },
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--fail-on-missing-index", action="store_true")
    parser.add_argument("--fail-on-date-function", action="store_true")
    parser.add_argument("--fail-on-full-scan", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload = build_baseline_payload()

    missing_index_keys: list[str] = []
    date_function_keys: list[str] = []
    full_scan_keys: list[str] = []
    plan = payload.get("timeline_query_plan", {})
    if isinstance(plan, dict):
        for key in ("journal", "card_session"):
            entry = plan.get(key, {})
            if not isinstance(entry, dict) or not bool(entry.get("index_detected")):
                missing_index_keys.append(key)
            if isinstance(entry, dict) and bool(entry.get("uses_date_function")):
                date_function_keys.append(key)
            if isinstance(entry, dict) and bool(entry.get("full_scan_detected")):
                full_scan_keys.append(key)

    if args.output:
        args.output.write_text(_canonical_json(payload), encoding="utf-8")
        print(f"[timeline-baseline] wrote: {args.output}")
    else:
        print(_canonical_json(payload), end="")

    if args.fail_on_missing_index and missing_index_keys:
        print(
            "[timeline-baseline] missing index in explain plan: "
            + ", ".join(sorted(missing_index_keys)),
            file=sys.stderr,
        )
        return 1
    if args.fail_on_date_function and date_function_keys:
        print(
            "[timeline-baseline] disallowed DATE(...) function detected in timeline SQL: "
            + ", ".join(sorted(date_function_keys)),
            file=sys.stderr,
        )
        return 1
    if args.fail_on_full_scan and full_scan_keys:
        print(
            "[timeline-baseline] forbidden full table scan detected in timeline SQL: "
            + ", ".join(sorted(full_scan_keys)),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
