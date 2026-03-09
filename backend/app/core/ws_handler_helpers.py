from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect


async def resolve_ws_auth_token(websocket: WebSocket) -> Optional[str]:
    """
    Resolve WebSocket auth token from cookie, query param, or first auth frame.
    Returns None when auth token cannot be resolved.
    """
    cookies = websocket.headers.get("cookie", "")
    auth_token: str | None = None
    if cookies:
        for cookie_pair in cookies.split(";"):
            key, _, value = cookie_pair.strip().partition("=")
            if key == "access_token" and value:
                auth_token = value
                break

    legacy_token = websocket.query_params.get("token")
    if auth_token:
        return auth_token
    if legacy_token:
        return legacy_token

    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        try:
            auth_msg = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        if isinstance(auth_msg, dict) and auth_msg.get("type") == "auth":
            return auth_msg.get("token")
        return None
    except asyncio.TimeoutError:
        raise
    except WebSocketDisconnect:
        raise


def resolve_ws_client_ip(websocket: WebSocket) -> str:
    forwarded_for = (websocket.headers.get("x-forwarded-for") or "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if websocket.client and websocket.client.host:
        return websocket.client.host
    return ""
