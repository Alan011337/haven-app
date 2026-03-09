from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.core.ws_handler_helpers import resolve_ws_auth_token, resolve_ws_client_ip


class _FakeWebSocket:
    def __init__(
        self,
        *,
        cookie: str = "",
        query_token: str | None = None,
        first_message: str = "",
        client_host: str = "127.0.0.1",
        forwarded_for: str = "",
    ) -> None:
        self.headers = {}
        if cookie:
            self.headers["cookie"] = cookie
        if forwarded_for:
            self.headers["x-forwarded-for"] = forwarded_for
        self.query_params = {}
        if query_token is not None:
            self.query_params["token"] = query_token
        self._first_message = first_message
        self.client = SimpleNamespace(host=client_host)

    async def receive_text(self) -> str:
        return self._first_message


class WsHandlerHelpersTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_ws_auth_token_prefers_cookie(self) -> None:
        ws = _FakeWebSocket(
            cookie="access_token=cookie-token; other=1",
            query_token="query-token",
        )
        token = await resolve_ws_auth_token(ws)
        self.assertEqual(token, "cookie-token")

    async def test_resolve_ws_auth_token_uses_query_fallback(self) -> None:
        ws = _FakeWebSocket(query_token="query-token")
        token = await resolve_ws_auth_token(ws)
        self.assertEqual(token, "query-token")

    async def test_resolve_ws_auth_token_uses_first_auth_message(self) -> None:
        ws = _FakeWebSocket(first_message='{"type":"auth","token":"frame-token"}')
        token = await resolve_ws_auth_token(ws)
        self.assertEqual(token, "frame-token")

    async def test_resolve_ws_auth_token_returns_none_on_invalid_frame(self) -> None:
        ws = _FakeWebSocket(first_message='{"type":"ping"}')
        token = await resolve_ws_auth_token(ws)
        self.assertIsNone(token)

    def test_resolve_ws_client_ip_prefers_forwarded_for(self) -> None:
        ws = _FakeWebSocket(forwarded_for="10.0.0.2, 10.0.0.3", client_host="192.168.1.2")
        self.assertEqual(resolve_ws_client_ip(ws), "10.0.0.2")

    def test_resolve_ws_client_ip_falls_back_to_client_host(self) -> None:
        ws = _FakeWebSocket(client_host="192.168.1.2")
        self.assertEqual(resolve_ws_client_ip(ws), "192.168.1.2")


if __name__ == "__main__":
    unittest.main()
