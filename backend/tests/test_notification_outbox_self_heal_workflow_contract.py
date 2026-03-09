from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "notification-outbox-self-heal.yml"


def test_notification_outbox_self_heal_workflow_exists() -> None:
    assert WORKFLOW_PATH.exists()


def test_notification_outbox_self_heal_workflow_contract() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "name: Notification Outbox Self-Heal Drill" in text
    assert "workflow_dispatch" in text
    assert "schedule:" in text
    assert "scripts/run_notification_outbox_self_heal.py" in text
    assert "config/notification_outbox_self_heal_policy.json" in text
    assert "notification-outbox-self-heal" in text
