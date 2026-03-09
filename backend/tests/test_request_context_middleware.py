import uuid
import unittest
from typing import Iterable
from unittest.mock import patch

from starlette.requests import Request
from starlette.responses import Response

from app.middleware.request_context import (
    RequestContextMiddleware,
    latency_ms_var,
    mode_var,
    partner_id_var,
    request_id_var,
    route_var,
    session_id_var,
    status_code_var,
    user_id_var,
)


async def _noop_app(scope, receive, send) -> None:  # pragma: no cover
    return None


def _build_request(
    *,
    headers: Iterable[tuple[bytes, bytes]] | None = None,
    path: str = "/health",
    query_string: bytes = b"",
) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string,
        "headers": list(headers or []),
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    return Request(scope)


class RequestContextMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    async def test_dispatch_sets_header_and_resets_context(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request(headers=[(b"x-request-id", b"req-abc-123")])

        async def call_next(_: Request) -> Response:
            self.assertEqual(request_id_var.get(), "req-abc-123")
            user_id_var.set("user-42")
            partner_id_var.set("partner-42")
            session_id_var.set("session-42")
            mode_var.set("DECK")
            return Response("ok")

        response = await middleware.dispatch(request, call_next)
        self.assertEqual(response.headers.get("x-request-id"), "req-abc-123")
        self.assertEqual(request_id_var.get(), "")
        self.assertEqual(user_id_var.get(), "")
        self.assertEqual(partner_id_var.get(), "")
        self.assertEqual(session_id_var.get(), "")
        self.assertEqual(mode_var.get(), "")
        self.assertEqual(route_var.get(), "")
        self.assertEqual(status_code_var.get(), "")
        self.assertEqual(latency_ms_var.get(), "")

    async def test_dispatch_generates_request_id_when_absent(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request()

        captured_id = ""

        async def call_next(_: Request) -> Response:
            nonlocal captured_id
            captured_id = request_id_var.get()
            self.assertTrue(captured_id)
            uuid.UUID(captured_id)
            return Response("ok")

        response = await middleware.dispatch(request, call_next)
        self.assertEqual(response.headers.get("x-request-id"), captured_id)
        self.assertEqual(request_id_var.get(), "")
        self.assertEqual(user_id_var.get(), "")
        self.assertEqual(partner_id_var.get(), "")
        self.assertEqual(session_id_var.get(), "")
        self.assertEqual(mode_var.get(), "")
        self.assertEqual(route_var.get(), "")
        self.assertEqual(status_code_var.get(), "")
        self.assertEqual(latency_ms_var.get(), "")

    async def test_dispatch_replaces_invalid_request_id_header(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request(headers=[(b"x-request-id", b"bad\nid")])

        captured_id = ""

        async def call_next(_: Request) -> Response:
            nonlocal captured_id
            captured_id = request_id_var.get()
            uuid.UUID(captured_id)
            return Response("ok")

        response = await middleware.dispatch(request, call_next)
        self.assertEqual(response.headers.get("x-request-id"), captured_id)
        self.assertNotEqual(captured_id, "bad\nid")
        self.assertEqual(request_id_var.get(), "")
        self.assertEqual(user_id_var.get(), "")
        self.assertEqual(partner_id_var.get(), "")
        self.assertEqual(session_id_var.get(), "")
        self.assertEqual(mode_var.get(), "")
        self.assertEqual(route_var.get(), "")
        self.assertEqual(status_code_var.get(), "")
        self.assertEqual(latency_ms_var.get(), "")

    async def test_dispatch_resets_context_even_when_handler_raises(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request(headers=[(b"x-request-id", b"req-ok-1")])

        async def call_next(_: Request) -> Response:
            self.assertEqual(request_id_var.get(), "req-ok-1")
            user_id_var.set("user-from-handler")
            partner_id_var.set("partner-from-handler")
            session_id_var.set("session-from-handler")
            mode_var.set("DAILY_RITUAL")
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            await middleware.dispatch(request, call_next)

        self.assertEqual(request_id_var.get(), "")
        self.assertEqual(user_id_var.get(), "")
        self.assertEqual(partner_id_var.get(), "")
        self.assertEqual(session_id_var.get(), "")
        self.assertEqual(mode_var.get(), "")
        self.assertEqual(route_var.get(), "")
        self.assertEqual(status_code_var.get(), "")
        self.assertEqual(latency_ms_var.get(), "")

    async def test_dispatch_sets_route_context_during_handler(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request(path="/api/cards/respond")

        async def call_next(_: Request) -> Response:
            self.assertEqual(route_var.get(), "/api/cards/respond")
            return Response("ok")

        response = await middleware.dispatch(request, call_next)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(route_var.get(), "")

    async def test_dispatch_extracts_session_and_mode_from_query_params(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request(
            path="/api/cards/123e4567-e89b-12d3-a456-426614174000/conversation",
            query_string=b"session_id=123e4567-e89b-12d3-a456-426614174111&mode=deck",
        )

        async def call_next(_: Request) -> Response:
            self.assertEqual(session_id_var.get(), "123e4567-e89b-12d3-a456-426614174111")
            self.assertEqual(mode_var.get(), "DECK")
            return Response("ok")

        response = await middleware.dispatch(request, call_next)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(session_id_var.get(), "")
        self.assertEqual(mode_var.get(), "")

    async def test_dispatch_infers_mode_from_path_when_not_provided(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request(path="/api/card-decks/history")

        async def call_next(_: Request) -> Response:
            self.assertEqual(mode_var.get(), "DECK")
            self.assertEqual(session_id_var.get(), "")
            return Response("ok")

        response = await middleware.dispatch(request, call_next)
        self.assertEqual(response.status_code, 200)

    async def test_dispatch_extracts_session_id_from_respond_path(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request(
            path="/api/card-decks/respond/123e4567-e89b-12d3-a456-426614174222"
        )

        async def call_next(_: Request) -> Response:
            self.assertEqual(session_id_var.get(), "123e4567-e89b-12d3-a456-426614174222")
            self.assertEqual(mode_var.get(), "DECK")
            return Response("ok")

        response = await middleware.dispatch(request, call_next)
        self.assertEqual(response.status_code, 200)

    async def test_dispatch_drops_invalid_session_id_values(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request(
            path="/api/card-decks/history",
            query_string=b"session_id=../../etc/passwd&mode=deck",
        )

        async def call_next(_: Request) -> Response:
            self.assertEqual(session_id_var.get(), "")
            self.assertEqual(mode_var.get(), "DECK")
            return Response("ok")

        response = await middleware.dispatch(request, call_next)
        self.assertEqual(response.status_code, 200)

    async def test_dispatch_rewrites_api_v2_path_and_preserves_original_route(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request(path="/api/v2/cards/draw")

        async def call_next(req: Request) -> Response:
            self.assertTrue(bool(req.scope.get("haven_api_v2_alias")))
            self.assertEqual(req.scope.get("path"), "/api/cards/draw")
            self.assertEqual(req.scope.get("haven_original_path"), "/api/v2/cards/draw")
            self.assertEqual(route_var.get(), "/api/v2/cards/draw")
            return Response("ok")

        response = await middleware.dispatch(request, call_next)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(route_var.get(), "")

    async def test_dispatch_rewrites_api_v2_root(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request(path="/api/v2")

        async def call_next(req: Request) -> Response:
            self.assertEqual(req.scope.get("path"), "/api")
            self.assertEqual(req.scope.get("haven_original_path"), "/api/v2")
            self.assertTrue(bool(req.scope.get("haven_api_v2_alias")))
            self.assertEqual(route_var.get(), "/api/v2")
            return Response("ok")

        response = await middleware.dispatch(request, call_next)
        self.assertEqual(response.status_code, 200)

    async def test_dispatch_normalizes_route_dynamic_segments(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request(
            path="/api/cards/123e4567-e89b-12d3-a456-426614174000/conversation/98765"
        )

        async def call_next(_: Request) -> Response:
            self.assertEqual(route_var.get(), "/api/cards/:uuid/conversation/:id")
            return Response("ok")

        response = await middleware.dispatch(request, call_next)
        self.assertEqual(response.status_code, 200)

    async def test_dispatch_route_normalization_can_be_disabled(self) -> None:
        middleware = RequestContextMiddleware(_noop_app)
        request = _build_request(
            path="/api/cards/123e4567-e89b-12d3-a456-426614174000/conversation/98765"
        )

        with patch("app.middleware.request_context.settings.LOG_ROUTE_NORMALIZE_DYNAMIC_SEGMENTS", False):
            async def call_next(_: Request) -> Response:
                self.assertEqual(
                    route_var.get(),
                    "/api/cards/123e4567-e89b-12d3-a456-426614174000/conversation/98765",
                )
                return Response("ok")

            response = await middleware.dispatch(request, call_next)
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
