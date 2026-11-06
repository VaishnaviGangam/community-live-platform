"""Community Live API: REST health endpoint and in-memory WebSocket chat."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Community Live API",
    description="A small real-time chat service for the Community Live portfolio project.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    """Validated chat payload sent by a connected visitor."""

    username: str = Field(min_length=1, max_length=24)
    text: str = Field(min_length=1, max_length=500)


class ConnectionManager:
    """Track active sockets and safely broadcast messages to the room."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info("Client connected; active connections=%d", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
        logger.info("Client disconnected; active connections=%d", len(self._connections))

    async def broadcast(self, payload: dict[str, Any]) -> None:
        message = json.dumps(payload)
        async with self._lock:
            connections = list(self._connections)

        stale: list[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception:
                logger.exception("Failed to send message to a WebSocket client")
                stale.append(connection)

        if stale:
            async with self._lock:
                for connection in stale:
                    self._connections.discard(connection)


manager = ConnectionManager()


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health check for local development and containers."""
    return {"status": "ok", "service": "community-live-api"}


@app.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket) -> None:
    """Accept validated chat messages and broadcast them to connected clients."""
    await manager.connect(websocket)
    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                message = ChatMessage.model_validate_json(raw_message)
            except ValidationError as exc:
                await websocket.send_json(
                    {"type": "error", "message": "Enter a name and a message (up to 500 characters)."}
                )
                logger.debug("Rejected invalid chat payload: %s", exc)
                continue

            payload = {
                "type": "message",
                "username": message.username.strip(),
                "text": message.text.strip(),
            }
            if not payload["username"] or not payload["text"]:
                await websocket.send_json(
                    {"type": "error", "message": "Name and message cannot be blank."}
                )
                continue

            await manager.broadcast(payload)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
        logger.exception("Unexpected WebSocket error")
