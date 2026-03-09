import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_api_inventory_owner_attestation.py"
_SPEC = importlib.util.spec_from_file_location("check_api_inventory_owner_attestation", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class ApiInventoryOwnerAttestationPolicyTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_owner_attestation_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_missing_owner_attestation(self) -> None:
        now = datetime(2026, 2, 17, 3, 15, tzinfo=timezone.utc)
        inventory_payload = {
            "entries": [
                {"owner_team": "backend-auth"},
                {"owner_team": "backend-core"},
            ]
        }
        attestation_payload = {
            "schema_version": _MODULE.ATTESTATION_SCHEMA_VERSION,
            "artifact_kind": _MODULE.ATTESTATION_ARTIFACT_KIND,
            "updated_at": "2026-02-17T03:15:00Z",
            "max_attestation_age_days": 90,
            "owners": [
                {
                    "owner_team": "backend-auth",
                    "attested_by": "test@haven.local",
                    "attested_at": "2026-02-17T03:15:00Z",
                    "codeowners_refs": ["/backend/app/api/login.py"],
                }
            ],
        }

        violations = _MODULE.collect_owner_attestation_violations(
            attestation_payload=attestation_payload,
            inventory_payload=inventory_payload,
            now_utc=now,
            codeowners_patterns={"/backend/app/api/login.py"},
        )

        self.assertTrue(any(v.reason == "missing_owner_attestation" for v in violations))

    def test_policy_rejects_stale_attestation(self) -> None:
        now = datetime(2026, 2, 17, 3, 15, tzinfo=timezone.utc)
        inventory_payload = {"entries": [{"owner_team": "backend-auth"}]}
        attestation_payload = {
            "schema_version": _MODULE.ATTESTATION_SCHEMA_VERSION,
            "artifact_kind": _MODULE.ATTESTATION_ARTIFACT_KIND,
            "updated_at": "2026-02-17T03:15:00Z",
            "max_attestation_age_days": 30,
            "owners": [
                {
                    "owner_team": "backend-auth",
                    "attested_by": "test@haven.local",
                    "attested_at": "2025-12-01T00:00:00Z",
                    "codeowners_refs": ["/backend/app/api/login.py"],
                }
            ],
        }

        violations = _MODULE.collect_owner_attestation_violations(
            attestation_payload=attestation_payload,
            inventory_payload=inventory_payload,
            now_utc=now,
            codeowners_patterns={"/backend/app/api/login.py"},
        )

        self.assertTrue(any(v.reason == "stale_attestation" for v in violations))

    def test_policy_rejects_codeowners_ref_not_in_codeowners(self) -> None:
        now = datetime(2026, 2, 17, 3, 15, tzinfo=timezone.utc)
        inventory_payload = {"entries": [{"owner_team": "backend-auth"}]}
        attestation_payload = {
            "schema_version": _MODULE.ATTESTATION_SCHEMA_VERSION,
            "artifact_kind": _MODULE.ATTESTATION_ARTIFACT_KIND,
            "updated_at": "2026-02-17T03:15:00Z",
            "max_attestation_age_days": 90,
            "owners": [
                {
                    "owner_team": "backend-auth",
                    "attested_by": "test@haven.local",
                    "attested_at": "2026-02-17T03:15:00Z",
                    "codeowners_refs": ["/backend/app/api/login.py"],
                }
            ],
        }

        violations = _MODULE.collect_owner_attestation_violations(
            attestation_payload=attestation_payload,
            inventory_payload=inventory_payload,
            now_utc=now,
            codeowners_patterns={"/backend/app/api/routers/billing.py"},
        )

        self.assertTrue(any(v.reason == "codeowners_ref_missing" for v in violations))

    def test_policy_rejects_attestation_expiring_soon(self) -> None:
        now = datetime(2026, 2, 17, 3, 15, tzinfo=timezone.utc)
        inventory_payload = {"entries": [{"owner_team": "backend-auth"}]}
        attestation_payload = {
            "schema_version": _MODULE.ATTESTATION_SCHEMA_VERSION,
            "artifact_kind": _MODULE.ATTESTATION_ARTIFACT_KIND,
            "updated_at": "2026-02-17T03:15:00Z",
            "max_attestation_age_days": 30,
            "min_attestation_days_remaining": 10,
            "owners": [
                {
                    "owner_team": "backend-auth",
                    "attested_by": "test@haven.local",
                    "attested_at": "2026-01-23T03:15:00Z",
                    "codeowners_refs": ["/backend/app/api/login.py"],
                }
            ],
        }

        violations = _MODULE.collect_owner_attestation_violations(
            attestation_payload=attestation_payload,
            inventory_payload=inventory_payload,
            now_utc=now,
            codeowners_patterns={"/backend/app/api/login.py"},
        )

        self.assertTrue(any(v.reason == "attestation_expiring_soon" for v in violations))


if __name__ == "__main__":
    unittest.main()
