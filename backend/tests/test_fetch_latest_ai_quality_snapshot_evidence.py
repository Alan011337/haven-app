import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "fetch_latest_ai_quality_snapshot_evidence.py"
_SPEC = importlib.util.spec_from_file_location("fetch_latest_ai_quality_snapshot_evidence", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def _zip_blob(entries: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return stream.getvalue()


class FetchLatestAIQualitySnapshotEvidenceTests(unittest.TestCase):
    def test_extract_artifact_file_uses_exact_path_first(self) -> None:
        blob = _zip_blob(
            {
                "docs/security/evidence/ai-quality-snapshot-latest.json": b'{"result":"pass"}',
                "ai-quality-snapshot-latest.json": b'{"result":"degraded"}',
            }
        )
        file_bytes, selected = _MODULE._extract_artifact_file(
            blob,
            artifact_file="docs/security/evidence/ai-quality-snapshot-latest.json",
        )
        self.assertEqual(selected, "docs/security/evidence/ai-quality-snapshot-latest.json")
        self.assertEqual(file_bytes, b'{"result":"pass"}')

    def test_extract_artifact_file_falls_back_to_basename(self) -> None:
        blob = _zip_blob({"nested/ai-quality-snapshot-latest.json": b'{"result":"pass"}'})
        file_bytes, selected = _MODULE._extract_artifact_file(
            blob,
            artifact_file="docs/security/evidence/ai-quality-snapshot-latest.json",
        )
        self.assertEqual(selected, "nested/ai-quality-snapshot-latest.json")
        self.assertEqual(file_bytes, b'{"result":"pass"}')

    def test_main_writes_output_when_fetch_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "latest.json"
            summary_path = Path(tmpdir) / "summary.json"
            payload_bytes = b'{"artifact_kind":"ai-quality-snapshot","evaluation":{"result":"pass"}}'
            meta = {
                "repository": "acme/haven",
                "workflow_file": ".github/workflows/ai-quality-snapshot.yml",
                "branch": "main",
                "workflow_run_id": 123,
                "artifact_name": "ai-quality-snapshot",
                "artifact_id": 456,
                "artifact_file": "docs/security/evidence/ai-quality-snapshot-latest.json",
                "archive_member": "docs/security/evidence/ai-quality-snapshot-latest.json",
            }
            with patch.dict(
                "os.environ",
                {"GITHUB_REPOSITORY": "acme/haven", "GITHUB_TOKEN": "token"},
                clear=False,
            ), patch.object(
                _MODULE,
                "fetch_latest_ai_quality_snapshot_evidence",
                return_value=(payload_bytes, meta),
            ):
                exit_code = _MODULE.main(
                    [
                        "--output",
                        str(output_path),
                        "--summary-path",
                        str(summary_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(output_path.read_bytes(), payload_bytes)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["result"], "pass")
            self.assertEqual(summary["meta"]["workflow_run_id"], 123)
            self.assertEqual(summary["meta"]["artifact_id"], 456)

    def test_main_skips_when_missing_evidence_and_allow_flag_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "latest.json"
            summary_path = Path(tmpdir) / "summary.json"
            with patch.dict(
                "os.environ",
                {"GITHUB_REPOSITORY": "acme/haven", "GITHUB_TOKEN": "token"},
                clear=False,
            ), patch.object(
                _MODULE,
                "fetch_latest_ai_quality_snapshot_evidence",
                side_effect=_MODULE.FetchEvidenceError("workflow_run_not_found"),
            ):
                exit_code = _MODULE.main(
                    [
                        "--allow-missing-evidence",
                        "--output",
                        str(output_path),
                        "--summary-path",
                        str(summary_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertFalse(output_path.exists())
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["result"], "skip")
            self.assertIn("workflow_run_not_found", summary["reasons"])

    def test_main_fails_on_non_skippable_fetch_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "summary.json"
            with patch.dict(
                "os.environ",
                {"GITHUB_REPOSITORY": "acme/haven", "GITHUB_TOKEN": "token"},
                clear=False,
            ), patch.object(
                _MODULE,
                "fetch_latest_ai_quality_snapshot_evidence",
                side_effect=_MODULE.FetchEvidenceError("github_request_error", detail="timeout"),
            ):
                exit_code = _MODULE.main(["--summary-path", str(summary_path)])

            self.assertEqual(exit_code, 1)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["result"], "fail")
            self.assertIn("github_request_error", summary["reasons"])


if __name__ == "__main__":
    unittest.main()
