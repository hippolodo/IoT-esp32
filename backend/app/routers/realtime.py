"""Authenticated WebSocket event delivery."""
import asyncio
import anyio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.auth import websocket_session_valid

WEBSOCKET_AUTH_TIMEOUT_SECONDS = 5
WEBSOCKET_SESSION_CHECK_SECONDS = 5
router = APIRouter()


# Mở /ws, kiểm tra Origin/token rồi đăng ký hàng đợi sự kiện cho client đã xác thực.
@router.websocket("/ws")
async def websocket(ws: WebSocket):
    settings = ws.app.state.settings
    hub = ws.app.state.hub
    sessions = ws.app.state.sessions
    origin = ws.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        await ws.close(code=1008)
        return
    await ws.accept()
    authorization = ws.headers.get("authorization", "").split()
    if len(authorization) == 2 and authorization[0].lower() == "bearer":
        token = authorization[1]
    else:
        token = None
    if token is None:
        try:
            # Browsers cannot set Authorization on the WebSocket handshake.
            # Receive credentials in the first frame instead of a URL query.
            auth = await asyncio.wait_for(ws.receive_json(), WEBSOCKET_AUTH_TIMEOUT_SECONDS)
        except WebSocketDisconnect:
            return
        except (asyncio.TimeoutError, ValueError, TypeError, KeyError):
            await ws.close(code=4401)
            return
        if isinstance(auth, dict) and auth.get("type") == "auth":
            token = auth.get("token")
        else:
            token = None
    if not await asyncio.to_thread(websocket_session_valid, token, sessions):
        await ws.close(code=4401)
        return
    await ws.send_json({"type": "authenticated"})
    queue = asyncio.Queue(maxsize=100)
    hub.subscribers.add(queue)

    # Gửi sự kiện đúng topic cho client và kiểm tra phiên còn hợp lệ, cả khi không có sự kiện.
    async def send_events():
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), WEBSOCKET_SESSION_CHECK_SECONDS)
            except asyncio.TimeoutError:
                event = None
            if not await asyncio.to_thread(websocket_session_valid, token, sessions):
                await ws.close(code=4401)
                group.cancel_scope.cancel()
                return
            if event is not None and ws.query_params.get("topic") in (None, event["topic"]):
                await ws.send_json(event)

    # Chờ client gửi dữ liệu để phát hiện ngắt kết nối và dọn tác vụ gửi.
    async def receive_events():
        while True:
            await ws.receive_text()

    try:
        async with anyio.create_task_group() as group:
            group.start_soon(send_events)
            try:
                await receive_events()
            except WebSocketDisconnect:
                pass
            finally:
                group.cancel_scope.cancel()
    finally:
        hub.subscribers.discard(queue)
