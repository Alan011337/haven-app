#!/usr/bin/env python3
"""Seed a deterministic local DB fixture for core-loop snapshot gates."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse

from sqlmodel import SQLModel, Session, create_engine, delete

from app.core.datetime_utils import utcnow
from app.models.events_log import EventsLog
from app.models.user import User

DEFAULT_DATABASE_URL = "sqlite:////tmp/core-loop-snapshot-release-gate-local.db"
DEFAULT_USER_TOTAL = 10
DEFAULT_COMPLETED_USERS = 4


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed a deterministic local fixture for core-loop snapshot checks."
    )
    parser.add_argument(
        "--database-url",
        default=DEFAULT_DATABASE_URL,
        help="Target database URL. Defaults to a dedicated /tmp sqlite database.",
    )
    parser.add_argument(
        "--user-total",
        type=int,
        default=DEFAULT_USER_TOTAL,
        help="Total active users to seed.",
    )
    parser.add_argument(
        "--completed-users",
        type=int,
        default=DEFAULT_COMPLETED_USERS,
        help="Users that also receive daily_loop_completed.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Allow resetting an existing local sqlite fixture database.",
    )
    return parser


def _sqlite_connect_args(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _resolve_sqlite_path(database_url: str) -> Path | None:
    parsed = urlparse(database_url)
    if parsed.scheme != "sqlite":
        return None
    if not parsed.path:
        return None
    return Path(parsed.path)


def _ensure_reset_allowed(database_url: str, *, reset: bool) -> None:
    if not reset:
        return
    sqlite_path = _resolve_sqlite_path(database_url)
    if sqlite_path is None:
        raise SystemExit("seed_core_loop_fixture --reset only supports sqlite database URLs")
    resolved = sqlite_path.resolve()
    allowed_roots = {
        Path("/tmp").resolve(),
        Path("/private/tmp").resolve(),
    }
    if not any(root == resolved or root in resolved.parents for root in allowed_roots):
        raise SystemExit("seed_core_loop_fixture --reset only allows /tmp sqlite fixture databases")


def _build_fixture_events(*, user_id: object, partner_user_id: object, prefix: str, include_completion: bool) -> list[EventsLog]:
    now = utcnow()
    rows = [
        EventsLog(
            user_id=user_id,
            partner_user_id=partner_user_id,
            event_name="daily_sync_submitted",
            event_id=f"{prefix}-sync",
            source="fixture",
            ts=now,
            dedupe_key=f"{prefix}-sync",
        ),
        EventsLog(
            user_id=user_id,
            partner_user_id=partner_user_id,
            event_name="daily_card_revealed",
            event_id=f"{prefix}-reveal",
            source="fixture",
            ts=now,
            dedupe_key=f"{prefix}-reveal",
        ),
        EventsLog(
            user_id=user_id,
            partner_user_id=partner_user_id,
            event_name="card_answer_submitted",
            event_id=f"{prefix}-answer",
            source="fixture",
            ts=now,
            dedupe_key=f"{prefix}-answer",
        ),
        EventsLog(
            user_id=user_id,
            partner_user_id=partner_user_id,
            event_name="appreciation_sent",
            event_id=f"{prefix}-appreciation",
            source="fixture",
            ts=now,
            dedupe_key=f"{prefix}-appreciation",
        ),
    ]
    if include_completion:
        rows.append(
            EventsLog(
                user_id=user_id,
                partner_user_id=partner_user_id,
                event_name="daily_loop_completed",
                event_id=f"{prefix}-completed",
                source="fixture",
                ts=now,
                dedupe_key=f"{prefix}-completed",
            )
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    user_total = max(2, int(args.user_total))
    completed_users = max(0, min(int(args.completed_users), user_total))
    _ensure_reset_allowed(args.database_url, reset=bool(args.reset))

    engine = create_engine(
        args.database_url,
        connect_args=_sqlite_connect_args(args.database_url),
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        if args.reset:
            session.exec(delete(EventsLog))
            session.exec(delete(User))
            session.commit()

        users: list[User] = []
        for index in range(user_total):
            user = User(
                email=f"core-loop-fixture-{index}@example.com",
                full_name=f"Core Loop Fixture {index}",
                hashed_password="fixture-hash",
            )
            session.add(user)
            users.append(user)
        session.commit()
        for user in users:
            session.refresh(user)

        events: list[EventsLog] = []
        for index, user in enumerate(users):
            partner = users[index ^ 1] if index % 2 == 0 and index + 1 < len(users) else (
                users[index - 1] if index % 2 == 1 else users[index]
            )
            events.extend(
                _build_fixture_events(
                    user_id=user.id,
                    partner_user_id=partner.id if partner.id != user.id else None,
                    prefix=f"user-{index}",
                    include_completion=index < completed_users,
                )
            )
        session.add_all(events)
        session.commit()

    print("[seed-core-loop-fixture] result")
    print(f"  database_url: {args.database_url}")
    print(f"  users_seeded: {user_total}")
    print(f"  completed_users_seeded: {completed_users}")
    print("  result: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
