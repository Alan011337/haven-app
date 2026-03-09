from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.card_response import CardResponse  # noqa: F401,E402
from app.models.journal import Journal  # noqa: F401,E402
from app.models.user import User  # noqa: F401,E402
from app.services.rate_limit import (  # noqa: E402
    enforce_card_response_create_rate_limit,
    enforce_journal_create_rate_limit,
)


class RateLimitScopeDimensionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.user_id = uuid.uuid4()
        self.partner_id = uuid.uuid4()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_journal_device_scope_blocks_second_hit(self) -> None:
        device_id = f"device-{uuid.uuid4().hex}"
        with Session(self.engine) as session:
            enforce_journal_create_rate_limit(
                session=session,
                user_id=self.user_id,
                partner_id=self.partner_id,
                limit_count=0,
                window_seconds=60,
                client_ip="127.0.0.1",
                device_id=device_id,
                ip_limit_count=0,
                device_limit_count=1,
                partner_pair_limit_count=0,
            )
            with self.assertRaises(HTTPException) as exc_info:
                enforce_journal_create_rate_limit(
                    session=session,
                    user_id=self.user_id,
                    partner_id=self.partner_id,
                    limit_count=0,
                    window_seconds=60,
                    client_ip="127.0.0.1",
                    device_id=device_id,
                    ip_limit_count=0,
                    device_limit_count=1,
                    partner_pair_limit_count=0,
                )
        self.assertEqual(exc_info.exception.status_code, 429)
        self.assertEqual(exc_info.exception.headers.get("X-RateLimit-Scope"), "device")

    def test_journal_partner_pair_scope_blocks_second_hit(self) -> None:
        with Session(self.engine) as session:
            enforce_journal_create_rate_limit(
                session=session,
                user_id=self.user_id,
                partner_id=self.partner_id,
                limit_count=0,
                window_seconds=60,
                client_ip="127.0.0.1",
                device_id=f"device-{uuid.uuid4().hex}",
                ip_limit_count=0,
                device_limit_count=0,
                partner_pair_limit_count=1,
            )
            with self.assertRaises(HTTPException) as exc_info:
                enforce_journal_create_rate_limit(
                    session=session,
                    user_id=self.user_id,
                    partner_id=self.partner_id,
                    limit_count=0,
                    window_seconds=60,
                    client_ip="127.0.0.1",
                    device_id=f"device-{uuid.uuid4().hex}",
                    ip_limit_count=0,
                    device_limit_count=0,
                    partner_pair_limit_count=1,
                )
        self.assertEqual(exc_info.exception.status_code, 429)
        self.assertEqual(exc_info.exception.headers.get("X-RateLimit-Scope"), "partner_pair")

    def test_card_device_scope_blocks_second_hit(self) -> None:
        device_id = f"device-{uuid.uuid4().hex}"
        with Session(self.engine) as session:
            enforce_card_response_create_rate_limit(
                session=session,
                user_id=self.user_id,
                partner_id=self.partner_id,
                limit_count=0,
                window_seconds=60,
                client_ip="127.0.0.1",
                device_id=device_id,
                ip_limit_count=0,
                device_limit_count=1,
                partner_pair_limit_count=0,
            )
            with self.assertRaises(HTTPException) as exc_info:
                enforce_card_response_create_rate_limit(
                    session=session,
                    user_id=self.user_id,
                    partner_id=self.partner_id,
                    limit_count=0,
                    window_seconds=60,
                    client_ip="127.0.0.1",
                    device_id=device_id,
                    ip_limit_count=0,
                    device_limit_count=1,
                    partner_pair_limit_count=0,
                )
        self.assertEqual(exc_info.exception.status_code, 429)
        self.assertEqual(exc_info.exception.headers.get("X-RateLimit-Scope"), "device")

    def test_card_partner_pair_scope_blocks_second_hit(self) -> None:
        with Session(self.engine) as session:
            enforce_card_response_create_rate_limit(
                session=session,
                user_id=self.user_id,
                partner_id=self.partner_id,
                limit_count=0,
                window_seconds=60,
                client_ip="127.0.0.1",
                device_id=f"device-{uuid.uuid4().hex}",
                ip_limit_count=0,
                device_limit_count=0,
                partner_pair_limit_count=1,
            )
            with self.assertRaises(HTTPException) as exc_info:
                enforce_card_response_create_rate_limit(
                    session=session,
                    user_id=self.user_id,
                    partner_id=self.partner_id,
                    limit_count=0,
                    window_seconds=60,
                    client_ip="127.0.0.1",
                    device_id=f"device-{uuid.uuid4().hex}",
                    ip_limit_count=0,
                    device_limit_count=0,
                    partner_pair_limit_count=1,
                )
        self.assertEqual(exc_info.exception.status_code, 429)
        self.assertEqual(exc_info.exception.headers.get("X-RateLimit-Scope"), "partner_pair")


if __name__ == "__main__":
    unittest.main()
