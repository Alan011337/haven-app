import logging
import unittest
from unittest.mock import Mock

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.error_handling import commit_with_error_handling, flush_with_error_handling


class ErrorHandlingLogRedactionTests(unittest.TestCase):
    def test_flush_conflict_log_masks_exception_details(self) -> None:
        session = Mock()
        session.flush.side_effect = IntegrityError(
            "insert into users(email) values('secret@example.com')",
            params=None,
            orig=Exception("duplicate key"),
        )
        logger = Mock(spec=logging.Logger)

        with self.assertRaises(HTTPException) as raised:
            flush_with_error_handling(session, logger=logger, action="create-user")

        self.assertEqual(raised.exception.status_code, 409)
        session.rollback.assert_called_once()
        logger.warning.assert_called_once()
        args = logger.warning.call_args.args
        self.assertEqual(args[0], "%s: integrity conflict on flush: reason=%s")
        self.assertEqual(args[1], "create-user")
        self.assertEqual(args[2], "IntegrityError")
        merged = " ".join(str(item) for item in args)
        self.assertNotIn("secret@example.com", merged)

    def test_commit_conflict_log_masks_exception_details(self) -> None:
        session = Mock()
        session.commit.side_effect = IntegrityError(
            "insert into journals(content) values('super-secret message')",
            params=None,
            orig=Exception("duplicate key"),
        )
        logger = Mock(spec=logging.Logger)

        with self.assertRaises(HTTPException) as raised:
            commit_with_error_handling(session, logger=logger, action="commit-journal")

        self.assertEqual(raised.exception.status_code, 409)
        session.rollback.assert_called_once()
        logger.warning.assert_called_once()
        args = logger.warning.call_args.args
        self.assertEqual(args[0], "%s: integrity conflict on commit: reason=%s")
        self.assertEqual(args[1], "commit-journal")
        self.assertEqual(args[2], "IntegrityError")
        merged = " ".join(str(item) for item in args)
        self.assertNotIn("super-secret", merged)

    def test_flush_sqlalchemy_error_log_masks_exception_details(self) -> None:
        session = Mock()
        session.flush.side_effect = SQLAlchemyError(
            "postgresql://svc:super-secret@db.internal:5432/haven flush failed"
        )
        logger = Mock(spec=logging.Logger)

        with self.assertRaises(HTTPException) as raised:
            flush_with_error_handling(session, logger=logger, action="flush-journal")

        self.assertEqual(raised.exception.status_code, 500)
        session.rollback.assert_called_once()
        logger.error.assert_called_once()
        args = logger.error.call_args.args
        self.assertEqual(args[0], "%s: database error on flush: reason=%s")
        self.assertEqual(args[1], "flush-journal")
        self.assertEqual(args[2], "SQLAlchemyError")
        merged = " ".join(str(item) for item in args)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("postgresql://", merged)

    def test_commit_sqlalchemy_error_log_masks_exception_details(self) -> None:
        session = Mock()
        session.commit.side_effect = SQLAlchemyError(
            "postgresql://svc:super-secret@db.internal:5432/haven commit failed"
        )
        logger = Mock(spec=logging.Logger)

        with self.assertRaises(HTTPException) as raised:
            commit_with_error_handling(session, logger=logger, action="commit-journal")

        self.assertEqual(raised.exception.status_code, 500)
        session.rollback.assert_called_once()
        logger.error.assert_called_once()
        args = logger.error.call_args.args
        self.assertEqual(args[0], "%s: database error on commit: reason=%s")
        self.assertEqual(args[1], "commit-journal")
        self.assertEqual(args[2], "SQLAlchemyError")
        merged = " ".join(str(item) for item in args)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("postgresql://", merged)


if __name__ == "__main__":
    unittest.main()
