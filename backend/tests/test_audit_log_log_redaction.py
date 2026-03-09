import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import audit_log as audit_log_module  # noqa: E402


class _FailingAuditSession:
    def __init__(self, *, fail_on_add: bool = False, fail_on_commit: bool = False) -> None:
        self.fail_on_add = fail_on_add
        self.fail_on_commit = fail_on_commit
        self.rollback_called = False

    def add(self, _obj) -> None:
        if self.fail_on_add:
            raise RuntimeError("postgresql://svc:super-secret@db.internal:5432/haven")

    def commit(self) -> None:
        if self.fail_on_commit:
            raise RuntimeError("redis://:super-secret@redis.internal:6379/0")

    def rollback(self) -> None:
        self.rollback_called = True


class AuditLogLogRedactionTests(unittest.TestCase):
    def test_best_effort_add_failure_logs_exception_type_only(self) -> None:
        session = _FailingAuditSession(fail_on_add=True)

        with self.assertLogs(audit_log_module.logger.name, level="ERROR") as captured:
            audit_log_module.record_audit_event_best_effort(
                session=session,  # type: ignore[arg-type]
                actor_user_id=None,
                action="TEST_AUDIT_ADD_FAIL",
                resource_type="system",
                commit=False,
            )

        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("postgresql://", merged)
        self.assertFalse(session.rollback_called)

    def test_best_effort_commit_failure_rolls_back_and_logs_exception_type_only(self) -> None:
        session = _FailingAuditSession(fail_on_commit=True)

        with self.assertLogs(audit_log_module.logger.name, level="ERROR") as captured:
            audit_log_module.record_audit_event_best_effort(
                session=session,  # type: ignore[arg-type]
                actor_user_id=None,
                action="TEST_AUDIT_COMMIT_FAIL",
                resource_type="system",
                commit=True,
            )

        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("redis://", merged)
        self.assertTrue(session.rollback_called)


if __name__ == "__main__":
    unittest.main()
