"""Logging bootstrap for request/user context propagation."""

from __future__ import annotations

import logging

from app.core.structured_logger import StructuredContextFilter

_STRUCTURED_LOGGER_NAMES = ("", "uvicorn", "uvicorn.error", "uvicorn.access")


def _has_structured_filter(target: logging.Filterer) -> bool:
    return any(isinstance(existing, StructuredContextFilter) for existing in target.filters)


def _attach_structured_filter(target: logging.Filterer) -> None:
    if _has_structured_filter(target):
        return
    target.addFilter(StructuredContextFilter())


def configure_structured_logging() -> None:
    """Attach StructuredContextFilter to root + uvicorn loggers and handlers."""
    for logger_name in _STRUCTURED_LOGGER_NAMES:
        logger = logging.getLogger(logger_name)
        _attach_structured_filter(logger)
        for handler in logger.handlers:
            _attach_structured_filter(handler)
