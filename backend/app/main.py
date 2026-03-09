# backend/app/main.py
from contextlib import asynccontextmanager
import json
import logging
import time
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
# jose imported lazily in websocket_endpoint to avoid blocking app load on some envs
# sqlmodel.Session imported lazily where used to avoid blocking app load on some envs
from sqlmodel import Session
# 引入 Routers (config.settings is lazy so Settings() runs on first access, not at import)
from app.core import config
from app.api import login, journals
from app.api.routers import admin, billing, cards, users, memory, mediation, reports
from app.api.routers.card_decks import router as card_decks_router
from app.api.routers.baseline import baseline_router, couple_goal_router
from app.api.routers.daily_sync import router as daily_sync_router
from app.api.routers.appreciations import router as appreciations_router
from app.api.routers.love_language import router as love_language_router
from app.api.routers.cooldown import router as cooldown_router
from app.api.routers.love_map import router as love_map_router
from app.api.routers.blueprint import router as blueprint_router
from app.core.datetime_utils import utcnow
from app.core.health_routes import get_health_router
from app.core.http_policy import (
    IDEMPOTENCY_EXEMPT_PATHS as _IDEMPOTENCY_EXEMPT_PATHS,
    IDEMPOTENCY_REQUIRED_METHODS,
    SECURITY_HEADER_EXCLUDED_PATHS as _SECURITY_HEADER_EXCLUDED_PATHS,
    SECURITY_RESPONSE_HEADERS,
    is_idempotency_exempt_path,
    is_security_header_excluded_path,
    normalize_path,
)
from app.core.settings_domains import get_ws_settings
from app.core.socket_manager import (
    init_socket_manager,
    shutdown_socket_manager,
    manager as _socket_manager_manager,
)
from app.core.ws_endpoint import run_ws_endpoint
from app.queue.journal_tasks import start_journal_queue_workers, stop_journal_queue_workers
from app.db.session import engine
from app.services.abuse_state_store_factory import create_abuse_state_store
from app.services.http_observability import http_observability
from app.services.ws_abuse_guard import WsAbuseGuard
from app.services.ws_runtime_metrics import ws_runtime_metrics
from app.services.api_idempotency_store import (
    build_request_hash,
    build_scope_fingerprint,
    load_replay_decision,
    max_request_body_bytes,
    normalize_idempotency_key,
    save_idempotency_response,
)
from app.services.posthog_events import capture_posthog_event
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.request_context import latency_ms_var, status_code_var
from app.middleware.request_context import request_id_var
from app.api.v2_contract import build_error_envelope, build_success_envelope
from app.core.logging_setup import configure_structured_logging
configure_structured_logging()
logger = logging.getLogger(__name__)

# Backward-compatible exports used by contract inventory scripts/tests.
IDEMPOTENCY_EXEMPT_PATHS = _IDEMPOTENCY_EXEMPT_PATHS
SECURITY_HEADER_EXCLUDED_PATHS = _SECURITY_HEADER_EXCLUDED_PATHS

APP_STARTED_AT = utcnow()
# Backward-compatible globals used by tests/patching hooks.
_ws_abuse_guard: WsAbuseGuard | None = None
ws_abuse_guard: WsAbuseGuard | None = None
manager = _socket_manager_manager


def _get_ws_abuse_guard() -> WsAbuseGuard:
    """Lazily initialize guard to keep module import/bootstrap path lightweight."""
    global _ws_abuse_guard, ws_abuse_guard
    if ws_abuse_guard is not None:
        _ws_abuse_guard = ws_abuse_guard
        return ws_abuse_guard
    if _ws_abuse_guard is not None:
        ws_abuse_guard = _ws_abuse_guard
        return _ws_abuse_guard

    ws_settings = get_ws_settings()
    _ws_abuse_guard = WsAbuseGuard(
        limit_count=ws_settings.message_rate_limit_count,
        window_seconds=ws_settings.message_rate_limit_window_seconds,
        backoff_seconds=ws_settings.message_backoff_seconds,
        max_payload_bytes=ws_settings.max_payload_bytes,
        state_store=create_abuse_state_store(scope="ws-message"),
    )
    ws_abuse_guard = _ws_abuse_guard
    return _ws_abuse_guard

# 1. Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Haven backend starting up")
    await init_socket_manager(config.settings.REDIS_URL)
    start_journal_queue_workers()
    try:
        yield
    finally:
        await stop_journal_queue_workers()
        await shutdown_socket_manager()
        # 🚀 Gracefully close the reusable Gemini HTTP client on shutdown
        try:
            from app.services.ai import _gemini_http_client
            if _gemini_http_client and not _gemini_http_client.is_closed:
                await _gemini_http_client.aclose()
                logger.info("Gemini HTTP client closed")
        except Exception:
            logger.debug("Gemini HTTP client cleanup skipped")
    logger.info("Haven backend shutdown complete")

# 2. 建立 app
app = FastAPI(
    title="Haven v2 API",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Device-Id",
        "X-Client-Id",
        "X-Request-Id",
        "X-Client-Ts",
        "Idempotency-Key",
    ],
)
app.add_middleware(RequestContextMiddleware)


def _cors_headers_for_request(request: Request) -> dict[str, str]:
    """Return CORS headers so error responses (e.g. 500) are not blocked by the browser."""
    origin = request.headers.get("origin", "").strip()
    if origin and origin in config.settings.CORS_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


async def _extract_response_body(response: Response) -> tuple[bytes, Response]:
    body = getattr(response, "body", None)
    body_iterator = getattr(response, "body_iterator", None)
    if isinstance(body, (bytes, bytearray)) and body:
        return bytes(body), response
    if isinstance(body, (bytes, bytearray)) and not body and body_iterator is None:
        return bytes(body), response
    if body_iterator is None:
        return b"", response

    chunks: list[bytes] = []
    async for chunk in body_iterator:
        if isinstance(chunk, bytes):
            chunks.append(chunk)
        else:
            chunks.append(str(chunk).encode("utf-8"))
    body_bytes = b"".join(chunks)

    passthrough_headers = {
        k: v
        for k, v in response.headers.items()
        if k.lower() not in {"content-length"}
    }
    rebuilt = Response(
        content=body_bytes,
        status_code=response.status_code,
        headers=passthrough_headers,
        media_type=response.media_type,
        background=response.background,
    )
    return body_bytes, rebuilt


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    headers = dict(_cors_headers_for_request(request))
    request_id = request_id_var.get() or request.headers.get("x-request-id", "-")
    if request.url.path.startswith("/api/"):
        message = str(exc.detail) if not isinstance(exc.detail, (dict, list)) else "Request failed."
        content = build_error_envelope(
            request_id=request_id,
            status_code=exc.status_code,
            message=message,
            details=exc.detail,
        )
    else:
        content = exc.detail if isinstance(exc.detail, (dict, list)) else {"detail": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=content, headers=headers)


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    headers = dict(_cors_headers_for_request(request))
    request_id = request_id_var.get() or request.headers.get("x-request-id", "-")
    if request.url.path.startswith("/api/"):
        message = str(exc.detail) if not isinstance(exc.detail, (dict, list)) else "Request failed."
        content = build_error_envelope(
            request_id=request_id,
            status_code=exc.status_code,
            message=message,
            details=exc.detail,
        )
    else:
        content = exc.detail if isinstance(exc.detail, (dict, list)) else {"detail": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=content, headers=headers)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log only exception type to avoid PII or request details in exception message (P0-H).
    logger.error(
        "Unhandled exception: %s",
        type(exc).__name__,
        exc_info=config.settings.LOG_INCLUDE_STACKTRACE,
    )
    headers = _cors_headers_for_request(request)
    request_id = request_id_var.get() or request.headers.get("x-request-id", "-")
    if request.url.path.startswith("/api/"):
        content = build_error_envelope(
            request_id=request_id,
            status_code=500,
            code="internal_server_error",
            message="Internal server error",
        )
    else:
        content = {"detail": "Internal server error"}
    return JSONResponse(
        status_code=500,
        content=content,
        headers=headers,
    )


@app.middleware("http")
async def append_security_headers(request: Request, call_next):
    original_path = str(request.scope.get("haven_original_path") or request.url.path)
    started = time.perf_counter()

    # Normalize to avoid trailing-slash mismatches in allowlist checks.
    normalized_path = normalize_path(original_path)
    is_api_request = normalized_path.startswith("/api/")
    is_idempotency_exempt = is_idempotency_exempt_path(normalized_path)
    idempotency_key: str | None = None
    idempotency_scope: str | None = None
    idempotency_request_hash: str | None = None
    idempotency_skip_reason: str | None = None

    if (
        request.method.upper() in IDEMPOTENCY_REQUIRED_METHODS
        and is_api_request
        and not is_idempotency_exempt
    ):
        idem = normalize_idempotency_key(request.headers.get("Idempotency-Key"))
        if not idem:
            rid = request_id_var.get() or request.headers.get("x-request-id", "-")
            return JSONResponse(
                status_code=400,
                content=build_error_envelope(
                    request_id=rid,
                    status_code=400,
                    code="missing_idempotency_key",
                    message="Idempotency-Key header is required for API write operations.",
                ),
                headers=_cors_headers_for_request(request),
            )
        idempotency_key = idem
        max_request_bytes = max_request_body_bytes()
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                content_length_int = int(content_length)
            except (TypeError, ValueError):
                content_length_int = -1
            if content_length_int > max_request_bytes:
                idempotency_skip_reason = "request_too_large"
                logger.info(
                    "Idempotency replay skipped due to content-length: path=%s content_length=%s max_request_bytes=%s",
                    normalized_path,
                    content_length_int,
                    max_request_bytes,
                )
        if not idempotency_skip_reason:
            request_body = await request.body()
            if len(request_body) > max_request_bytes:
                idempotency_skip_reason = "request_too_large"
                logger.info(
                    "Idempotency replay skipped due to request body size: path=%s request_bytes=%s max_request_bytes=%s",
                    normalized_path,
                    len(request_body),
                    max_request_bytes,
                )
            else:
                idempotency_scope = build_scope_fingerprint(
                    request=request,
                    normalized_path=normalized_path,
                )
                idempotency_request_hash = build_request_hash(
                    method=request.method,
                    normalized_path=normalized_path,
                    query_string=request.url.query or "",
                    body_bytes=request_body or b"",
                )

        if idempotency_scope and idempotency_request_hash:
            try:
                with Session(engine) as idem_session:
                    replay_decision = load_replay_decision(
                        session=idem_session,
                        scope_fingerprint=idempotency_scope,
                        idempotency_key=idempotency_key,
                        request_hash=idempotency_request_hash,
                    )
            except Exception:
                replay_decision = None
                logger.warning(
                    "Idempotency replay lookup failed; fallback to normal execution: path=%s",
                    normalized_path,
                )
        else:
            replay_decision = None

        if replay_decision is not None:
            if replay_decision.status == "mismatch":
                rid = request_id_var.get() or request.headers.get("x-request-id", "-")
                latency_ms = (time.perf_counter() - started) * 1000
                status_code_var.set("409")
                latency_ms_var.set(f"{latency_ms:.3f}")
                http_observability.record(latency_ms=latency_ms, status_code=409)
                return JSONResponse(
                    status_code=409,
                    content=build_error_envelope(
                        request_id=rid,
                        status_code=409,
                        code="idempotency_payload_mismatch",
                        message="Idempotency-Key reuse with a different payload is not allowed.",
                    ),
                    headers=_cors_headers_for_request(request),
                )
            if replay_decision.status == "replay" and replay_decision.payload is not None:
                replay_headers = dict(_cors_headers_for_request(request))
                replay_headers["X-Idempotency-Replayed"] = "true"
                replay_response = JSONResponse(
                    status_code=int(replay_decision.status_code or 200),
                    content=replay_decision.payload,
                    headers=replay_headers,
                )
                if not is_security_header_excluded_path(request.url.path):
                    for header_name, header_value in SECURITY_RESPONSE_HEADERS.items():
                        if header_name not in replay_response.headers:
                            replay_response.headers[header_name] = header_value
                latency_ms = (time.perf_counter() - started) * 1000
                status_code_var.set(str(replay_response.status_code))
                latency_ms_var.set(f"{latency_ms:.3f}")
                http_observability.record(latency_ms=latency_ms, status_code=replay_response.status_code)
                return replay_response

    try:
        response = await call_next(request)
    except Exception:
        latency_ms = (time.perf_counter() - started) * 1000
        status_code_var.set("500")
        latency_ms_var.set(f"{latency_ms:.3f}")
        http_observability.record(latency_ms=latency_ms, status_code=500)
        raise
    decoded_response_payload: dict | None = None
    if request.url.path.startswith("/api/"):
        content_type = (response.headers.get("content-type") or "").lower()
        has_set_cookie = "set-cookie" in {k.lower() for k in response.headers.keys()}
        is_json_response = "application/json" in content_type
        should_wrap_envelope = response.status_code < 400 and is_json_response and not has_set_cookie
        should_decode_for_idempotency = bool(
            idempotency_key
            and idempotency_scope
            and idempotency_request_hash
            and response.status_code < 500
            and is_json_response
        )
        if should_wrap_envelope or should_decode_for_idempotency:
            body, response = await _extract_response_body(response)
            if should_wrap_envelope:
                try:
                    if body:
                        decoded = json.loads(body.decode("utf-8"))
                        if not (
                            isinstance(decoded, dict)
                            and {"data", "meta", "error"}.issubset(decoded.keys())
                        ):
                            request_id = request_id_var.get() or request.headers.get("x-request-id", "-")
                            wrapped = build_success_envelope(request_id=request_id, data=decoded)
                            passthrough_headers = {
                                k: v
                                for k, v in response.headers.items()
                                if k.lower() not in {"content-length"}
                            }
                            response = JSONResponse(
                                status_code=response.status_code,
                                content=wrapped,
                                headers=passthrough_headers,
                            )
                            decoded_response_payload = wrapped
                        elif isinstance(decoded, dict):
                            decoded_response_payload = decoded
                except Exception:
                    logger.debug("API response envelope wrapping skipped")
            elif is_json_response and body:
                try:
                    decoded = json.loads(body.decode("utf-8"))
                    if isinstance(decoded, dict):
                        decoded_response_payload = decoded
                except Exception:
                    logger.debug("API response decode skipped")

    if (
        idempotency_key
        and idempotency_scope
        and idempotency_request_hash
        and response.status_code < 500
    ):
        try:
            payload_to_persist = decoded_response_payload
            if payload_to_persist:
                with Session(engine) as idem_session:
                    persisted = save_idempotency_response(
                        session=idem_session,
                        scope_fingerprint=idempotency_scope,
                        idempotency_key=idempotency_key,
                        request_hash=idempotency_request_hash,
                        method=request.method,
                        route_path=normalized_path,
                        status_code=response.status_code,
                        payload=payload_to_persist,
                    )
                    if persisted:
                        idem_session.commit()
        except Exception:
            logger.warning(
                "Idempotency response persistence failed: path=%s",
                normalized_path,
            )

    latency_ms = (time.perf_counter() - started) * 1000
    status_code_var.set(str(response.status_code))
    latency_ms_var.set(f"{latency_ms:.3f}")
    http_observability.record(latency_ms=latency_ms, status_code=response.status_code)
    if request.method.upper() == "OPTIONS" and is_api_request and response.status_code >= 400:
        capture_posthog_event(
            event_name="cors_preflight_failed",
            distinct_id="system",
            properties={
                "status_code": response.status_code,
                "reason": "preflight_rejected",
            },
        )
    if not is_security_header_excluded_path(request.url.path):
        for header_name, header_value in SECURITY_RESPONSE_HEADERS.items():
            if header_name not in response.headers:
                response.headers[header_name] = header_value
    if idempotency_skip_reason and request.url.path.startswith("/api/"):
        response.headers["X-Idempotency-Skipped"] = idempotency_skip_reason
    return response


# 4. WebSocket 路徑
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    ws_abuse_guard = _get_ws_abuse_guard()
    await run_ws_endpoint(
        websocket=websocket,
        user_id=user_id,
        ws_abuse_guard=ws_abuse_guard,
        ws_runtime_metrics=ws_runtime_metrics,
        engine=engine,
        settings=config.settings,
        logger=logger,
    )

# 5. 註冊路由
_API_V1_V2_ROUTERS: list[tuple] = [
    (login.router, "/auth", ["auth"]),
    (users.router, "/users", ["users"]),
    (journals.router, "/journals", ["journals"]),
    (cards.router, "/cards", ["cards"]),
    (card_decks_router, "/card-decks", ["card-decks"]),
    (memory.router, "/memory", ["memory"]),
    (mediation.router, "/mediation", ["mediation"]),
    (billing.router, "/billing", ["billing"]),
    (admin.router, "/admin", ["admin"]),
    (reports.router, "/reports", ["reports"]),
    (baseline_router, "/baseline", None),
    (couple_goal_router, "/couple-goal", None),
    (daily_sync_router, "/daily-sync", None),
    (appreciations_router, "/appreciations", None),
    (love_language_router, "/love-languages", None),
    (cooldown_router, "/cooldown", None),
    (love_map_router, "/love-map", None),
    (blueprint_router, "/blueprint", None),
]

for router, suffix, tags in _API_V1_V2_ROUTERS:
    include_kwargs = {"prefix": f"/api{suffix}"}
    if tags:
        include_kwargs["tags"] = tags
    app.include_router(router, **include_kwargs)

app.include_router(get_health_router(APP_STARTED_AT, app.title, app.version))
