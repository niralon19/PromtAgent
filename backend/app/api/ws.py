"""WebSocket endpoint with topic-based routing."""
from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

log = structlog.get_logger(__name__)

router = APIRouter(tags=["websocket"])

_connections: set[WebSocket] = set()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    _connections.add(websocket)
    log.info("ws_client_connected", total=len(_connections))
    try:
        while True:
            # Keep alive — client can send topic subscriptions as JSON
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(websocket)
        log.info("ws_client_disconnected", total=len(_connections))


async def broadcast(event: str, data: dict[str, Any]) -> None:
    """Broadcast an event to all connected WebSocket clients."""
    if not _connections:
        return
    payload = json.dumps({"event": event, "data": data})
    dead: set[WebSocket] = set()
    for ws in list(_connections):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _connections.difference_update(dead)
