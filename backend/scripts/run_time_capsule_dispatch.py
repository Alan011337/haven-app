#!/usr/bin/env python3
"""
P2-C Time Capsule: Daily dispatch. For each user with partner, fetch memories from one year ago
today; if any, send time_capsule notification to both partners (push/in_app_ws per matrix).

Usage: run from cron (e.g. 08:00 daily). Requires DB and notification matrix.
  cd backend && PYTHONPATH=. python scripts/run_time_capsule_dispatch.py
"""

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

if __name__ == "__main__":
    _backend = Path(__file__).resolve().parent.parent
    if str(_backend) not in sys.path:
        sys.path.insert(0, str(_backend))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    from sqlmodel import Session, select
    from app.db.session import engine
    from app.models.user import User
    from app.services.memory_archive import get_time_capsule_memory
    from app.services.notification_payloads import build_partner_notification_payload
    from app.services.notification import queue_partner_notification

    today = date.today()
    exact_date = today - timedelta(days=365)
    logger.info("Time capsule dispatch: exact_date=%s", exact_date)

    with Session(engine) as session:
        users_with_partner = list(
            session.exec(select(User).where(User.partner_id.isnot(None), User.deleted_at.is_(None)))
        )
        partner_ids = [u.partner_id for u in users_with_partner if u.partner_id]
        partners_by_id: dict = {}
        if partner_ids:
            for row in session.exec(select(User).where(User.id.in_(partner_ids))):
                partners_by_id[row.id] = row
        # Dedupe by pair (A,B) == (B,A)
        seen_pairs: set[tuple] = set()
        sent = 0
        for user in users_with_partner:
            partner_id = user.partner_id
            if not partner_id:
                continue
            partner = partners_by_id.get(partner_id)
            if not partner or partner.partner_id != user.id:
                continue
            pair = (min(user.id, partner_id), max(user.id, partner_id))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            # Pass 1: exact anniversary date
            memory = get_time_capsule_memory(
                session=session,
                user_id=user.id,
                partner_id=partner_id,
                from_date=exact_date,
                to_date=exact_date,
            )
            # Pass 2: widen ±3 days if exact date has no content
            if not memory:
                memory = get_time_capsule_memory(
                    session=session,
                    user_id=user.id,
                    partner_id=partner_id,
                    from_date=exact_date - timedelta(days=3),
                    to_date=exact_date + timedelta(days=3),
                )
            if not memory:
                continue

            scope_id = f"time_capsule:{exact_date.isoformat()}"
            # Notify partner from user
            payload_a = build_partner_notification_payload(
                session=session,
                sender_user=user,
                event_type="time_capsule",
                scope_id=scope_id,
                source_session_id=None,
                partner_user_id=partner_id,
            )
            if payload_a:
                queue_partner_notification(
                    action_type="time_capsule",
                    event_type="time_capsule",
                    **payload_a,
                )
                sent += 1
            # Notify user from partner
            payload_b = build_partner_notification_payload(
                session=session,
                sender_user=partner,
                event_type="time_capsule",
                scope_id=scope_id,
                source_session_id=None,
                partner_user_id=user.id,
            )
            if payload_b:
                queue_partner_notification(
                    action_type="time_capsule",
                    event_type="time_capsule",
                    **payload_b,
                )
                sent += 1

    logger.info("Time capsule dispatch done: pairs=%s notifications_sent=%s", len(seen_pairs), sent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
