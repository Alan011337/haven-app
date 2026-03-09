from app.core.config import settings
from app.core.settings_manifest import SETTINGS_DOMAIN_MANIFEST, validate_manifest_against_settings


def test_settings_manifest_is_non_empty() -> None:
    assert SETTINGS_DOMAIN_MANIFEST
    assert all(SETTINGS_DOMAIN_MANIFEST.values())


def test_settings_manifest_keys_exist_on_settings() -> None:
    report = validate_manifest_against_settings(settings)
    assert report
    assert all(not missing for missing in report.values())

