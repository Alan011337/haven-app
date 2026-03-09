"""Compatibility shim: expose `app.api.routers.users` as the legacy `routes` module."""

from __future__ import annotations

import sys

from app.api.routers.users import routes as _routes

# Preserve historical patch/import surface:
# tests and runtime hooks reference `app.api.routers.users.<symbol>`.
sys.modules[__name__] = _routes
