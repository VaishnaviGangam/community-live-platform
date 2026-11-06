# Architecture — Milestone 1

## Overview

Community Live is split into a single-page React client and a FastAPI service. The client communicates with the service through a WebSocket connection for chat messages and an HTTP endpoint for health checks.

## Components

- **React + Vite:** renders the room, message feed, connection state, and message composer.
- **FastAPI:** exposes `GET /health` and `WS /ws/chat`.
- **ConnectionManager:** tracks active WebSocket connections and broadcasts messages to the current in-memory room.

## Message lifecycle

1. Browser creates a WebSocket to `/ws/chat`.
2. API accepts the connection and registers it with the connection manager.
3. Client sends JSON containing `username` and `text`.
4. Pydantic validates the payload (name 1–24 chars, message 1–500 chars).
5. API broadcasts a message object to active connections.
6. React appends the message to the feed.

## Current limitations

- No identity verification; names are display labels only.
- No persistent storage; messages are held by connected clients and are not saved.
- The connection manager is in-process and is not suitable for multi-instance deployment.
- There is no moderation or rate limiting yet.
- Participant count currently indicates whether this browser is connected, not the total server room population.

## Planned evolution

1. Add PostgreSQL persistence and SQLAlchemy models/migrations.
2. Add registration, authentication, and channel membership.
3. Add room-level presence and moderation controls.
4. Add Redis pub/sub for horizontally scaled WebSocket broadcasting.
5. Add a React Native client and deployment observability.
