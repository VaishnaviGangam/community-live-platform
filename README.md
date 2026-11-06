# Community Live

A full-stack, Twitch-inspired community chat application built as a learning portfolio project. The first milestone focuses on a real-time chat room with a React client and a FastAPI WebSocket service.

> Status: **Milestone 1 — starter implementation**. Authentication, persistent chat history, moderation tools, and streaming playback are planned, not implemented yet.

## Goals

- Build a responsive chat experience for online communities.
- Send and receive messages over a WebSocket connection.
- Keep the frontend and API independently runnable.
- Add automated tests and a repeatable Docker-based development setup.

## Architecture

```text
community-live-platform/
├── frontend/       React + Vite client
├── backend/        FastAPI REST and WebSocket service
├── docs/           Architecture and roadmap
└── .github/        CI workflow
```

### Current message flow

1. The React client opens a WebSocket connection to `/ws/chat`.
2. A visitor submits a message with a display name.
3. The API validates the message and broadcasts it to connected clients.
4. The UI displays incoming messages in the shared room.

Messages currently live in server memory and are lost when the backend restarts. PostgreSQL persistence will be added in a later milestone.

## Run locally

### Backend

Requires Python 3.11 or newer.

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

The API is available at http://localhost:8000 and interactive API docs at http://localhost:8000/docs.

### Frontend

Requires Node.js 20 or newer.

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally http://localhost:5173).

### Docker Compose

From the repository root:

```bash
docker compose up --build
```

The frontend is served at http://localhost:5173 and the API at http://localhost:8000.

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

## Roadmap

- [x] React chat interface and WebSocket message exchange
- [x] FastAPI WebSocket endpoint
- [x] Input validation and basic automated tests
- [x] Docker Compose development environment
- [ ] PostgreSQL message persistence and migrations
- [ ] User registration and authentication
- [ ] Channel membership and online presence
- [ ] Moderation: delete, timeout, and report workflows
- [ ] React Native companion client
- [ ] Deployment, monitoring, and screenshots

## Open-source references

This project is an independent learning implementation. It is not affiliated with Twitch and does not copy Twitch's branding or proprietary code. The implementation uses public framework documentation:

- [React](https://react.dev/)
- [Vite](https://vite.dev/guide/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [WebSockets](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

## License

MIT — see [LICENSE](LICENSE).
