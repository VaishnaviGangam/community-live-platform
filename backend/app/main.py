"""Community Live API: REST endpoints and persistent WebSocket chat."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Community Live API",
    description="A real-time community chat service with persistent message history.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_database_tables() -> None:
    """Create tables for the starter app; production migrations are a future step."""
    Base.metadata.create_all(bind=engine)


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
def health() -> dict[str, str]:
    """Simple health check for local development and containers."""
    return {"status": "ok", "service": "community-live-api"}


@app.get("/api/messages")
def get_messages(limit: int = Query(default=50, ge=1, le=100)) -> list[dict[str, Any]]:
    """Return the most recent messages in chronological order."""
    with SessionLocal() as session:
        rows = session.scalars(
            select(Message).order_by(Message.created_at.desc(), Message.id.desc()).limit(limit)
        ).all()
        rows.reverse()
        return [
            {
                "id": row.id,
                "type": "message",
                "username": row.username,
                "text": row.text,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]


@app.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket) -> None:
    """Validate, persist, and broadcast chat messages."""
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

            username = message.username.strip()
            text = message.text.strip()
            if not username or not text:
                await websocket.send_json(
                    {"type": "error", "message": "Name and message cannot be blank."}
                )
                continue

            with SessionLocal() as session:
                row = Message(username=username, text=text, created_at=datetime.now(timezone.utc))
                session.add(row)
                session.commit()
                session.refresh(row)
                payload = {
                    "id": row.id,
                    "type": "message",
                    "username": row.username,
                    "text": row.text,
                    "created_at": row.created_at.isoformat(),
                }

            await manager.broadcast(payload)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
        logger.exception("Unexpected WebSocket error")
