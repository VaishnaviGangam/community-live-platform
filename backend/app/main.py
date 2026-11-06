"""Community Live API with account authentication and persistent WebSocket chat."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, ValidationError
from pwdlib import PasswordHash
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.database import Base, SessionLocal, engine
from app.models import Message, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "local-development-only-change-this-secret-before-deployment")
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)

app = FastAPI(
    title="Community Live API",
    description="Authenticated real-time community chat with persistent message history.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
def create_database_tables() -> None:
    """Create tables for local development; use migrations before production schema changes."""
    Base.metadata.create_all(bind=engine)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=24, pattern=r"^[A-Za-z0-9_]+$")
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ChatMessage(BaseModel):
    text: str = Field(min_length=1, max_length=500)


def public_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat(),
    }


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def user_from_token(token: str) -> User | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        return None
    with SessionLocal() as session:
        return session.get(User, user_id)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    user = user_from_token(credentials.credentials)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token.")
    return user


class ConnectionManager:
    """Track active sockets and safely broadcast messages to the shared room."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

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
    return {"status": "ok", "service": "community-live-api"}


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> dict[str, Any]:
    email = payload.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    with SessionLocal() as session:
        existing = session.scalar(
            select(User).where(or_(User.email == email, User.username == payload.username))
        )
        if existing:
            raise HTTPException(status_code=409, detail="That email or username is already registered.")
        user = User(
            username=payload.username,
            email=email,
            password_hash=password_hasher.hash(payload.password),
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        try:
            session.commit()
            session.refresh(user)
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="That email or username is already registered.")
        return {"access_token": create_access_token(user), "token_type": "bearer", "user": public_user(user)}


@app.post("/api/auth/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    email = payload.email.strip().lower()
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is None or not password_hasher.verify(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Incorrect email or password.")
        return {"access_token": create_access_token(user), "token_type": "bearer", "user": public_user(user)}


@app.get("/api/auth/me")
def read_current_user(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    return public_user(current_user)


@app.get("/api/messages")
def get_messages(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    del current_user
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
async def chat_socket(websocket: WebSocket, token: str = Query(default="")) -> None:
    """Only authenticated accounts can join and send messages to the chat room."""
    user = user_from_token(token) if token else None
    if user is None:
        await websocket.close(code=4401, reason="Authentication required")
        return

    await manager.connect(websocket)
    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                message = ChatMessage.model_validate_json(raw_message)
            except ValidationError:
                await websocket.send_json({"type": "error", "message": "Enter a message up to 500 characters."})
                continue

            text = message.text.strip()
            if not text:
                await websocket.send_json({"type": "error", "message": "Message cannot be blank."})
                continue

            with SessionLocal() as session:
                row = Message(username=user.username, text=text, created_at=datetime.now(timezone.utc))
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
