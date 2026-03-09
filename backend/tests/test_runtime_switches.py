from app.core.runtime_switches import RuntimeFeatureSwitches, get_runtime_feature_switches


def test_runtime_switches_shape() -> None:
    switches = get_runtime_feature_switches()
    assert isinstance(switches, RuntimeFeatureSwitches)
    assert isinstance(switches.websocket_enabled, bool)
    assert isinstance(switches.webpush_enabled, bool)
    assert isinstance(switches.push_notifications_enabled, bool)
    assert isinstance(switches.email_notifications_enabled, bool)
    assert isinstance(switches.timeline_cursor_enabled, bool)
    assert isinstance(switches.safety_mode_enabled, bool)
