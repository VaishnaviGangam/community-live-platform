# Community Live

A full-stack, Twitch-inspired community chat application built as an independent software engineering portfolio project. It pairs a React + TypeScript client with a FastAPI WebSocket service and PostgreSQL message storage.

> Status: **Milestone 2 — persistent real-time chat foundation.** The current implementation supports one shared room, display-name messaging, persisted message history, and local Docker development. Authentication, moderation, multi-room support, and streaming playback are not implemented yet.

## Features

- Responsive React + TypeScript chat interface.
- Real-time message delivery with FastAPI WebSockets.
- PostgreSQL persistence for chat messages.
- REST endpoint to load the latest 1–100 messages.
- Server-side input validation and basic error responses.
- Automated backend tests and GitHub Actions CI.
- Docker Compose stack for the web client, API, and database.

## Architecture

```text
community-live-platform/
├── frontend/       React + Vite + TypeScript client
├── backend/
│   ├── app/        FastAPI routes, SQLAlchemy models and database setup
│   └── tests/      API and WebSocket tests
├── docs/           Architecture and roadmap
└── .github/        CI workflow
```

### Message flow

1. The browser loads recent chat history from `GET /api/messages`.
2. The client opens a WebSocket connection to `/ws/chat`.
3. A visitor submits a display name and message.
4. FastAPI validates the payload and stores it in PostgreSQL.
5. The API broadcasts the saved message to connected clients.

The local Compose stack includes PostgreSQL 16. When running the API directly without setting `DATABASE_URL`, it uses a local SQLite database file for convenience.

## Run with Docker Compose

Requires Docker Desktop or Docker Engine with the Compose plugin.

```bash
git clone https://github.com/VaishnaviGangam/community-live-platform.git
cd community-live-platform
docker compose up --build
```

- Web client: http://localhost:5173
- API health: http://localhost:8000/health
- API documentation: http://localhost:8000/docs
- Recent messages: http://localhost:8000/api/messages
- PostgreSQL: localhost:5432

To stop the stack:

```bash
docker compose down
```

To remove the local database volume as well (this deletes local chat history):

```bash
docker compose down -v
```

## Run locally without Docker

### Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend (Node.js 20+)

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

If the API runs on a different host, set `VITE_API_URL` and `VITE_WS_URL` in the frontend environment.

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

The backend tests cover the health endpoint, WebSocket message validation/delivery, persisted history, and history limit validation.

## Roadmap

- [x] React chat interface and WebSocket messaging
- [x] FastAPI WebSocket endpoint and payload validation
- [x] PostgreSQL persistence and message history endpoint
- [x] Docker Compose development environment
- [x] Backend test suite and CI workflow
- [ ] Database migrations with Alembic
- [ ] User registration and authentication
- [ ] Room membership and accurate online presence
- [ ] Moderation: delete, timeout, and report workflows
- [ ] Redis pub/sub for multi-instance WebSocket delivery
- [ ] React Native companion client
- [ ] Deployment, monitoring, and screenshots

## Open-source references

This is an independent learning implementation, not affiliated with Twitch. Frameworks and libraries are used according to their public documentation:

- [React](https://react.dev/)
- [Vite](https://vite.dev/guide/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [PostgreSQL](https://www.postgresql.org/docs/)

## License

MIT — see [LICENSE](LICENSE).
