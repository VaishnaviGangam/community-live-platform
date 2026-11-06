# Architecture — Milestone 2

## Overview

Community Live is split into a React + TypeScript single-page client and a FastAPI service. The client loads message history over HTTP and exchanges new messages over WebSockets. SQLAlchemy persists chat messages in PostgreSQL when the app runs through Docker Compose.

## Components

- **React + Vite:** renders the room, message feed, connection state, and message composer.
- **FastAPI:** exposes `GET /health`, `GET /api/messages`, and `WS /ws/chat`.
- **SQLAlchemy:** maps chat messages to the relational `messages` table.
- **PostgreSQL:** stores messages across API restarts and container restarts (using a named Docker volume).
- **ConnectionManager:** tracks active WebSocket connections in the current API process and broadcasts saved messages.

## Message lifecycle

1. Browser requests the latest messages from `GET /api/messages?limit=50`.
2. Browser connects to `/ws/chat`.
3. Client sends JSON containing `username` and `text`.
4. Pydantic validates the payload (name 1–24 chars, message 1–500 chars).
5. API inserts the message and commits the database transaction.
6. API broadcasts the saved message, including its database ID and timestamp, to connected clients.
7. React appends the message to the feed.

## Data model

### messages

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| username | String(24) | Display name; not an authenticated identity |
| text | Text | Message body |
| created_at | Timestamp | UTC timestamp |

## Local environment

Docker Compose starts PostgreSQL, the API, and the Vite development server. The API waits for the database health check before starting. For a direct local API run, the default database is SQLite unless `DATABASE_URL` is set.

## Current limitations

- Display names are not authenticated identities and can be impersonated.
- No message edit/delete, moderation, or rate limiting.
- One shared room only; no room membership model.
- Online count is a local connection indicator, not an authoritative server-wide participant count.
- WebSocket connections are tracked in process memory; multiple API instances need a shared pub/sub layer.
- Tables are created with SQLAlchemy `create_all`; Alembic migrations are planned before schema evolution.
- CORS origins are configured for local development and should be set explicitly for deployment.

## Planned evolution

1. Add Alembic migrations and schema versioning.
2. Add user registration, authentication, and channel membership.
3. Add room-level presence and moderation controls.
4. Add Redis pub/sub for horizontally scaled WebSocket broadcasting.
5. Add a React Native client and deployment observability.
