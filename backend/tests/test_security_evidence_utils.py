import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import security_evidence_utils


class SecurityEvidenceUtilsTests(unittest.TestCase):
    def test_parse_iso8601_accepts_and_rejects_values(self) -> None:
        self.assertTrue(security_evidence_utils.parse_iso8601("2026-03-05T00:00:00Z"))
        self.assertFalse(security_evidence_utils.parse_iso8601("not-a-date"))

    def test_resolve_latest_evidence_path_uses_kind_pattern(self) -> None:
        with TemporaryDirectory() as td:
            evidence_dir = Path(td)
            first = evidence_dir / "p0-drill-20260101T000000Z.json"
            second = evidence_dir / "p0-drill-20260102T000000Z.json"
            first.write_text("{}", encoding="utf-8")
            second.write_text("{}", encoding="utf-8")

            resolved = security_evidence_utils.resolve_latest_evidence_path(
                evidence_dir=evidence_dir,
                kind="p0-drill",
            )
            self.assertEqual(resolved, second)


if __name__ == "__main__":
    unittest.main()
