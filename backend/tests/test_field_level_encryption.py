import unittest
import uuid
import base64
import os
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from app.core.config import settings
from app.core.field_encryption import (
    ENCRYPTED_PREFIX,
    FieldEncryptionConfigError,
    decrypt_field_value,
    encrypt_field_value,
)
from app.models.analysis import Analysis
from app.models.card import Card, CardCategory
from app.models.card_response import CardResponse, ResponseStatus
from app.models.journal import Journal
from app.models.user import User


def _valid_key() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")


class FieldLevelEncryptionTests(unittest.TestCase):
    def test_encrypt_and_decrypt_roundtrip_when_enabled(self) -> None:
        key = _valid_key()
        with patch.object(settings, "FIELD_LEVEL_ENCRYPTION_ENABLED", True), patch.object(
            settings, "FIELD_LEVEL_ENCRYPTION_KEY", key
        ):
            encrypted = encrypt_field_value("secret-message")
            self.assertIsNotNone(encrypted)
            self.assertTrue(encrypted.startswith(ENCRYPTED_PREFIX))
            self.assertNotEqual(encrypted, "secret-message")
            self.assertEqual(decrypt_field_value(encrypted), "secret-message")

    def test_encrypt_passthrough_when_disabled(self) -> None:
        with patch.object(settings, "FIELD_LEVEL_ENCRYPTION_ENABLED", False), patch.object(
            settings, "FIELD_LEVEL_ENCRYPTION_KEY", None
        ):
            self.assertEqual(encrypt_field_value("plain-text"), "plain-text")
            self.assertEqual(decrypt_field_value("plain-text"), "plain-text")

    def test_encrypt_raises_when_enabled_without_key(self) -> None:
        with patch.object(settings, "FIELD_LEVEL_ENCRYPTION_ENABLED", True), patch.object(
            settings, "FIELD_LEVEL_ENCRYPTION_KEY", None
        ):
            with self.assertRaises(FieldEncryptionConfigError):
                encrypt_field_value("sensitive")

    def test_journal_and_analysis_values_are_encrypted_at_rest(self) -> None:
        key = _valid_key()
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        try:
            with patch.object(settings, "FIELD_LEVEL_ENCRYPTION_ENABLED", True), patch.object(
                settings, "FIELD_LEVEL_ENCRYPTION_KEY", key
            ):
                SQLModel.metadata.create_all(engine)

                user_id = uuid.uuid4()
                with Session(engine) as session:
                    user = User(
                        id=user_id,
                        email="enc-user@example.com",
                        hashed_password="hashed-password",
                    )
                    session.add(user)
                    session.commit()

                    card = Card(
                        category=CardCategory.DAILY_VIBE,
                        title="encrypted-card",
                        description="desc",
                        question="q",
                        difficulty_level=1,
                    )
                    session.add(card)
                    session.commit()
                    session.refresh(card)

                    journal = Journal(content="journal-secret", user_id=user_id)
                    session.add(journal)
                    session.commit()
                    session.refresh(journal)

                    analysis = Analysis(
                        journal_id=journal.id,
                        emotional_needs="needs-secret",
                        advice_for_user="advice-secret",
                    )
                    session.add(analysis)
                    card_response = CardResponse(
                        card_id=card.id,
                        user_id=user_id,
                        content="response-secret",
                        status=ResponseStatus.PENDING,
                        is_initiator=True,
                    )
                    session.add(card_response)
                    session.commit()

                    raw_journal_content = session.exec(
                        text("SELECT content FROM journals")
                    ).one()
                    self.assertNotEqual(raw_journal_content[0], "journal-secret")
                    self.assertTrue(str(raw_journal_content[0]).startswith(ENCRYPTED_PREFIX))

                    raw_analysis_value = session.exec(
                        text("SELECT emotional_needs FROM analyses")
                    ).one()
                    self.assertNotEqual(raw_analysis_value[0], "needs-secret")
                    self.assertTrue(str(raw_analysis_value[0]).startswith(ENCRYPTED_PREFIX))

                    raw_response_content = session.exec(
                        text("SELECT content FROM card_responses")
                    ).one()
                    self.assertNotEqual(raw_response_content[0], "response-secret")
                    self.assertTrue(str(raw_response_content[0]).startswith(ENCRYPTED_PREFIX))

                    loaded_journal = session.get(Journal, journal.id)
                    self.assertIsNotNone(loaded_journal)
                    assert loaded_journal is not None
                    self.assertEqual(loaded_journal.content, "journal-secret")

                    loaded_analysis = session.exec(
                        select(Analysis).where(Analysis.journal_id == journal.id)
                    ).one()
                    self.assertEqual(loaded_analysis.emotional_needs, "needs-secret")
                    self.assertEqual(loaded_analysis.advice_for_user, "advice-secret")

                    loaded_response = session.get(CardResponse, card_response.id)
                    self.assertIsNotNone(loaded_response)
                    assert loaded_response is not None
                    self.assertEqual(loaded_response.content, "response-secret")
        finally:
            engine.dispose()

    def test_legacy_plaintext_rows_remain_readable_after_enable(self) -> None:
        key = _valid_key()
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        try:
            with patch.object(settings, "FIELD_LEVEL_ENCRYPTION_ENABLED", False), patch.object(
                settings, "FIELD_LEVEL_ENCRYPTION_KEY", None
            ):
                SQLModel.metadata.create_all(engine)
                with Session(engine) as session:
                    user = User(
                        email="legacy-user@example.com",
                        hashed_password="hashed-password",
                    )
                    session.add(user)
                    session.commit()
                    session.refresh(user)

                    card = Card(
                        category=CardCategory.DAILY_VIBE,
                        title="legacy-card",
                        description="desc",
                        question="q",
                        difficulty_level=1,
                    )
                    session.add(card)
                    session.commit()
                    session.refresh(card)

                    journal = Journal(content="legacy-plain", user_id=user.id)
                    session.add(journal)
                    card_response = CardResponse(
                        card_id=card.id,
                        user_id=user.id,
                        content="legacy-response-plain",
                        status=ResponseStatus.PENDING,
                        is_initiator=True,
                    )
                    session.add(card_response)
                    session.commit()
                    session.refresh(journal)
                    session.refresh(card_response)
                    journal_id = journal.id
                    response_id = card_response.id

            with patch.object(settings, "FIELD_LEVEL_ENCRYPTION_ENABLED", True), patch.object(
                settings, "FIELD_LEVEL_ENCRYPTION_KEY", key
            ):
                with Session(engine) as session:
                    loaded_journal = session.get(Journal, journal_id)
                    self.assertIsNotNone(loaded_journal)
                    assert loaded_journal is not None
                    self.assertEqual(loaded_journal.content, "legacy-plain")
                    loaded_response = session.get(CardResponse, response_id)
                    self.assertIsNotNone(loaded_response)
                    assert loaded_response is not None
                    self.assertEqual(loaded_response.content, "legacy-response-plain")
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
