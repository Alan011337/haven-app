# Lazy settings: pydantic_settings is loaded only on first access to avoid startup
# hang on some macOS/Python envs. See _settings_impl.py for the Settings class.
_cached_settings: "object | None" = None


def __getattr__(name: str) -> "object":
    if name == "settings":
        global _cached_settings
        if _cached_settings is None:
            from app.core._settings_impl import Settings
            _cached_settings = Settings()
        return _cached_settings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
