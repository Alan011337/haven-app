import os
import subprocess
import sys
import unittest
from pathlib import Path


class BolaSubjectMatrixTests(unittest.TestCase):
    """Aggregated BOLA subject matrix smoke for core resources."""

    def test_core_resources_have_legal_and_illegal_subject_coverage(self) -> None:
        legal_case_ids = [
            "tests/test_user_authorization_matrix.py::UserAuthorizationMatrixTests::test_read_user_allows_self",
            "tests/test_journal_authorization_matrix.py::JournalAuthorizationMatrixTests::test_delete_journal_allows_owner",
            "tests/test_card_authorization_matrix.py::CardAuthorizationMatrixTests::test_respond_allows_owner_to_update_own_response",
            "tests/test_card_deck_authorization_matrix.py::CardDeckAuthorizationMatrixTests::test_deck_respond_allows_creator",
            "tests/test_notification_authorization_matrix.py::NotificationAuthorizationMatrixTests::test_mark_single_read_updates_owner_event_only",
            "tests/test_billing_authorization_matrix.py::BillingAuthorizationMatrixTests::test_reconciliation_is_scoped_to_current_user",
            "tests/test_memory_authorization_matrix.py::MemoryAuthorizationMatrixTests::test_timeline_allows_current_user_only",
        ]
        illegal_case_ids = [
            "tests/test_user_authorization_matrix.py::UserAuthorizationMatrixTests::test_read_user_rejects_non_partner",
            "tests/test_journal_authorization_matrix.py::JournalAuthorizationMatrixTests::test_delete_journal_rejects_non_owner",
            "tests/test_card_authorization_matrix.py::CardAuthorizationMatrixTests::test_respond_does_not_allow_other_user_to_overwrite_existing_response",
            "tests/test_card_deck_authorization_matrix.py::CardDeckAuthorizationMatrixTests::test_deck_respond_rejects_non_participant",
            "tests/test_notification_authorization_matrix.py::NotificationAuthorizationMatrixTests::test_mark_single_read_rejects_other_user_event",
            "tests/test_billing_authorization_matrix.py::BillingAuthorizationMatrixTests::test_state_change_idempotency_key_isolated_per_user",
            "tests/test_memory_authorization_matrix.py::MemoryAuthorizationMatrixTests::test_timeline_rejects_cross_user_data",
        ]

        backend_root = Path(__file__).resolve().parents[2]
        python_bin = backend_root / ".venv-gate" / "bin" / "python"
        if not python_bin.exists():
            python_bin = Path(sys.executable)

        failures: list[str] = []
        for case_id in legal_case_ids + illegal_case_ids:
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONPATH"] = "."
            result = subprocess.run(
                [
                    str(python_bin),
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    case_id,
                ],
                cwd=str(backend_root),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                stdout = (result.stdout or "").strip()
                details = stderr if stderr else stdout
                failures.append(f"{case_id}: {details}")

        if failures:
            self.fail("BOLA subject matrix aggregate failed:\n" + "\n\n".join(failures))


if __name__ == "__main__":
    unittest.main()
