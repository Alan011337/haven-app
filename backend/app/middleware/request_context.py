import uuid
import contextvars
import re
from collections.abc import Iterable

from app.core.config import settings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='')
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('user_id', default='')
partner_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('partner_id', default='')
session_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('session_id', default='')
mode_var: contextvars.ContextVar[str] = contextvars.ContextVar('mode', default='')
route_var: contextvars.ContextVar[str] = contextvars.ContextVar('route', default='')
status_code_var: contextvars.ContextVar[str] = contextvars.ContextVar('status_code', default='')
latency_ms_var: contextvars.ContextVar[str] = contextvars.ContextVar('latency_ms', default='')
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SESSION_ID_PATTERN = re.compile(r"^[0-9a-fA-F-]{36}$")
MODE_PATTERN = re.compile(r"^[A-Z_]{1,32}$")
RESPOND_SESSION_PATH_PATTERN = re.compile(
    r"^/api/card-decks/respond/(?P<session_id>[0-9a-fA-F-]{36})$"
)
API_V2_PREFIX = "/api/v2"
UUID_SEGMENT_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
INTEGER_SEGMENT_PATTERN = re.compile(r"^[0-9]{2,}$")
HEX_TOKEN_SEGMENT_PATTERN = re.compile(r"^[0-9a-fA-F]{16,}$")


def _normalize_request_id(raw_value: str | None) -> str:
    candidate = (raw_value or "").strip()
    if not candidate:
        return str(uuid.uuid4())
    if not REQUEST_ID_PATTERN.fullmatch(candidate):
        return str(uuid.uuid4())
    return candidate


def _normalize_mode(raw_value: str | None) -> str:
    candidate = (raw_value or "").strip().upper()
    if not candidate:
        return ""
    if not MODE_PATTERN.fullmatch(candidate):
        return ""
    return candidate


def _normalize_session_id(raw_value: str | None) -> str:
    candidate = (raw_value or "").strip()
    if not candidate:
        return ""
    if not SESSION_ID_PATTERN.fullmatch(candidate):
        return ""
    try:
        return str(uuid.UUID(candidate))
    except ValueError:
        return ""


def _pick_first(values: Iterable[str | None]) -> str:
    for value in values:
        normalized = (value or "").strip()
        if normalized:
            return normalized
    return ""


def _infer_mode_from_path(path: str) -> str:
    if path.startswith("/api/card-decks"):
        return "DECK"
    if path.startswith("/api/cards"):
        return "DAILY_RITUAL"
    if path.startswith("/api/journals"):
        return "JOURNAL"
    if path.startswith("/api/billing"):
        return "BILLING"
    return ""


def _extract_session_and_mode(request: Request) -> tuple[str, str]:
    path = request.url.path
    session_id = _normalize_session_id(
        _pick_first(
            (
                request.headers.get("x-session-id"),
                request.headers.get("x-haven-session-id"),
                request.query_params.get("session_id"),
            )
        )
    )
    if not session_id:
        matched = RESPOND_SESSION_PATH_PATTERN.match(path)
        if matched:
            session_id = _normalize_session_id(matched.group("session_id"))

    mode = _normalize_mode(
        _pick_first(
            (
                request.headers.get("x-haven-mode"),
                request.query_params.get("mode"),
            )
        )
    )
    if not mode:
        mode = _infer_mode_from_path(path)
    return session_id, mode


def _normalize_route_label(path: str) -> str:
    if not bool(getattr(settings, "LOG_ROUTE_NORMALIZE_DYNAMIC_SEGMENTS", True)):
        return path
    if not path.startswith("/"):
        return path
    normalized_parts: list[str] = []
    for part in path.split("/"):
        if not part:
            continue
        if UUID_SEGMENT_PATTERN.fullmatch(part):
            normalized_parts.append(":uuid")
            continue
        if INTEGER_SEGMENT_PATTERN.fullmatch(part):
            normalized_parts.append(":id")
            continue
        if HEX_TOKEN_SEGMENT_PATTERN.fullmatch(part):
            normalized_parts.append(":token")
            continue
        normalized_parts.append(part)
    return "/" + "/".join(normalized_parts)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        original_path = str(request.scope.get("path") or "")
        is_v2_alias = False
        if original_path == API_V2_PREFIX:
            request.scope["path"] = "/api"
            request.scope["raw_path"] = b"/api"
            is_v2_alias = True
        elif original_path.startswith(f"{API_V2_PREFIX}/"):
            rewritten_path = f"/api/{original_path[len(API_V2_PREFIX) + 1:]}"
            request.scope["path"] = rewritten_path
            request.scope["raw_path"] = rewritten_path.encode("utf-8")
            is_v2_alias = True

        request.scope["haven_original_path"] = original_path or str(request.scope.get("path") or "")
        request.scope["haven_api_v2_alias"] = is_v2_alias

        rid = _normalize_request_id(request.headers.get('x-request-id'))
        session_id, mode = _extract_session_and_mode(request)
        raw_route = str(request.scope.get("haven_original_path") or request.url.path)
        route = _normalize_route_label(raw_route)
        rid_token = request_id_var.set(rid)
        uid_token = user_id_var.set('')
        pid_token = partner_id_var.set('')
        sid_token = session_id_var.set(session_id)
        mode_token = mode_var.set(mode)
        route_token = route_var.set(route)
        status_token = status_code_var.set('')
        latency_token = latency_ms_var.set('')
        try:
            response = await call_next(request)
            response.headers['x-request-id'] = rid
            return response
        finally:
            # Prevent context leakage across requests in long-lived worker tasks.
            mode_var.reset(mode_token)
            session_id_var.reset(sid_token)
            partner_id_var.reset(pid_token)
            user_id_var.reset(uid_token)
            request_id_var.reset(rid_token)
            route_var.reset(route_token)
            status_code_var.reset(status_token)
            latency_ms_var.reset(latency_token)
