#!/usr/bin/env python3
"""
P2-D Active Care: Cron job. Find pairs with no interaction for 3 consecutive days,
send a light "ice-breaker / 抽卡邀請" push to both (via active_care notification).

No interaction = no journal and no completed card response from either user in the last 3 days.

Usage: run daily (e.g. 09:00). Requires DB + notification matrix (active_care trigger).
  cd backend && PYTHONPATH=. python scripts/run_active_care_dispatch.py
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

ACTIVE_CARE_NO_INTERACTION_DAYS = 3


def main() -> int:
    from sqlmodel import Session, select, func
    from app.db.session import engine
    from app.models.user import User
    from app.models.journal import Journal
    from app.models.card_response import CardResponse
    from app.services.notification_payloads import build_partner_notification_payload
    from app.services.notification import queue_partner_notification

    today = date.today()
    cutoff = today - timedelta(days=ACTIVE_CARE_NO_INTERACTION_DAYS)
    logger.info("Active care dispatch: cutoff=%s (no interaction since)", cutoff)

    with Session(engine) as session:
        users_with_partner = list(
            session.exec(select(User).where(User.partner_id.isnot(None), User.deleted_at.is_(None)))
        )
        seen_pairs: set[tuple] = set()
        sent = 0
        for user in users_with_partner:
            partner_id = user.partner_id
            if not partner_id:
                continue
            partner = session.get(User, partner_id)
            if not partner or partner.partner_id != user.id:
                continue
            pair = (min(user.id, partner_id), max(user.id, partner_id))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            # Last journal by either user
            last_journal = session.exec(
                select(func.max(Journal.created_at)).where(
                    Journal.user_id.in_([user.id, partner_id]),
                    Journal.deleted_at.is_(None),
                )
            ).one()
            # Last card response by either user
            last_response = session.exec(
                select(func.max(CardResponse.created_at)).where(
                    CardResponse.user_id.in_([user.id, partner_id]),
                    CardResponse.deleted_at.is_(None),
                )
            ).one()
            def _to_date(v):
                if v is None:
                    return None
                return getattr(v, "date", lambda: v)()

            last_activity = None
            if last_journal:
                last_activity = _to_date(last_journal)
            if last_response:
                resp_date = _to_date(last_response)
                if resp_date and (last_activity is None or resp_date > last_activity):
                    last_activity = resp_date
            if last_activity is not None and last_activity > cutoff:
                continue

            scope_id = f"active_care:{today.isoformat()}"
            for sender, receiver in ((user, partner), (partner, user)):
                payload = build_partner_notification_payload(
                    session=session,
                    sender_user=sender,
                    event_type="active_care",
                    scope_id=scope_id,
                    source_session_id=None,
                    partner_user_id=receiver.id,
                )
                if payload:
                    queue_partner_notification(
                        action_type="active_care",
                        event_type="active_care",
                        **payload,
                    )
                    sent += 1

    logger.info("Active care dispatch done: pairs=%s notifications_sent=%s", len(seen_pairs), sent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
