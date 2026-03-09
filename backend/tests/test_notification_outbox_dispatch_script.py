from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_notification_outbox_dispatch.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("run_notification_outbox_dispatch", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dispatch_script_loop_mode_respects_max_iterations(monkeypatch) -> None:
    module = _load_script_module()

    class _DummyLock:
        def __init__(self, *args, **kwargs) -> None:
            self.acquired = False

        def acquire(self) -> bool:
            self.acquired = True
            return True

        def release(self) -> None:
            self.acquired = False

    async def _fake_process_notification_outbox_batch(**kwargs):
        return {
            "selected": 1,
            "sent": 1,
            "retried": 0,
            "dead": 0,
            "errors": 0,
            "base_limit": 10,
            "selected_limit": 10,
            "backlog_depth": 0,
            "oldest_pending_age_seconds": 0,
            "adaptive_enabled": 1,
        }

    monkeypatch.setattr(module, "time", type("_T", (), {"sleep": staticmethod(lambda *_: None)})())
    monkeypatch.setattr("app.services.worker_lock.WorkerSingletonLock", _DummyLock)
    monkeypatch.setattr(
        "app.services.notification_outbox.auto_replay_dead_notification_outbox",
        lambda **kwargs: {
            "enabled": 1,
            "triggered": 0,
            "dead_rows": 0,
            "dead_letter_rate": 0.0,
            "replayed": 0,
            "errors": 0,
        },
    )
    monkeypatch.setattr(
        "app.services.notification_outbox.replay_dead_notification_outbox",
        lambda **kwargs: {"selected": 0, "replayed": 0, "errors": 0},
    )
    monkeypatch.setattr(
        "app.services.notification_outbox.process_notification_outbox_batch",
        _fake_process_notification_outbox_batch,
    )
    monkeypatch.setattr(
        "app.services.notification_outbox.get_notification_outbox_stale_processing_count",
        lambda: 0,
    )
    monkeypatch.setattr(
        module,
        "_parse_args",
        lambda: argparse.Namespace(
            limit=10,
            disable_adaptive=False,
            replay_dead=False,
            replay_limit=100,
            reset_attempt_count=False,
            replay_only=False,
            disable_auto_replay=False,
            lock_name="notification-outbox-dispatch",
            loop=True,
            interval_seconds=1,
            max_iterations=2,
            heartbeat_every=1,
        ),
    )

    result = module.main()
    assert result == 0
