# Community Live

An independent full-stack community chat portfolio project built with React, TypeScript, FastAPI, WebSockets, SQLAlchemy, and PostgreSQL.

> **Current milestone: 3 — authenticated real-time chat foundation.** Users can register, sign in, view their account profile, load persisted chat history, and send messages over an authenticated WebSocket connection. This is a learning portfolio project, not affiliated with Twitch.

## Features

- Responsive React + TypeScript client.
- Account registration with unique username and email.
- Passwords hashed with Argon2; raw passwords are never stored.
- JWT bearer access tokens with configurable expiry.
- Protected account profile and chat history endpoints.
- Authenticated WebSocket chat; the server derives the sender identity from the verified token.
- PostgreSQL persistence for accounts and chat messages.
- Backend tests and GitHub Actions CI.
- Docker Compose development environment.

## Architecture

```text
community-live-platform/
├── frontend/       React + Vite + TypeScript client
├── backend/
│   ├── app/        FastAPI routes, auth, SQLAlchemy models
│   └── tests/      API, authentication and WebSocket tests
├── docs/           Architecture and roadmap
└── .github/        CI workflow
```

### Authentication flow

1. A visitor submits registration details to `POST /api/auth/register`.
2. The API validates the username, email, and password length.
3. The password is hashed with Argon2 before the account is stored.
4. The API returns a signed JWT access token.
5. The React client sends the token as a bearer token to protected HTTP endpoints and as a query parameter when opening the WebSocket.
6. The API verifies the token and uses the account's stored username for chat messages. A client cannot choose another sender name in the chat payload.

### API endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | `/health` | Public | Health check |
| POST | `/api/auth/register` | Public | Create an account |
| POST | `/api/auth/login` | Public | Sign in |
| GET | `/api/auth/me` | Bearer token | Get signed-in account |
| GET | `/api/messages?limit=50` | Bearer token | Load recent chat history |
| WS | `/ws/chat?token=...` | JWT required | Authenticated real-time chat |

## Run with Docker Compose

Requires Docker Desktop or Docker Engine with the Compose plugin.

```bash
git clone https://github.com/VaishnaviGangam/community-live-platform.git
cd community-live-platform
docker compose up --build
```

- Web client: http://localhost:5173
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- PostgreSQL: localhost:5432

Open the web client, create an account with a username, email, and password of at least 10 characters, then sign in and send a chat message.

To stop the stack:

```bash
docker compose down
```

To remove the local database volume and all local accounts/messages:

```bash
docker compose down -v
```

## Run locally without Docker

### Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Set `DATABASE_URL` if you want to use PostgreSQL; otherwise the API uses a local SQLite file.

### Frontend (Node.js 20+)

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` and `VITE_WS_URL` if the API is not running on localhost.

## Environment variables

- `DATABASE_URL`: SQLAlchemy database URL.
- `JWT_SECRET_KEY`: secret used to sign access tokens. Set a long, random value outside local development.
- `ACCESS_TOKEN_MINUTES`: token lifetime in minutes (default 60).
- `VITE_API_URL`: API base URL for the browser.
- `VITE_WS_URL`: WebSocket URL for the browser.

**Security note:** Docker Compose includes a development-only JWT secret and database password so the project can run locally. Replace both before any shared or public deployment. Use HTTPS/WSS in production. This starter stores the browser access token in localStorage for ease of development; a production deployment should consider secure, HttpOnly, SameSite cookies, CSRF protections, rate limiting, email verification, password reset, and secret management. The current schema uses SQLAlchemy `create_all`; add Alembic migrations before evolving a deployed database.

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

Tests cover health, registration, duplicate account rejection, password hashing, login, protected endpoints, authenticated WebSocket delivery, invalid messages, and authentication enforcement.

## Roadmap

- [x] React chat interface and WebSocket messaging
- [x] PostgreSQL persistence and message history
- [x] Account registration and login
- [x] Argon2 password hashing and JWT authentication
- [x] Protected profile, history, and WebSocket routes
- [x] Docker Compose, tests, and CI workflow
- [ ] Alembic database migrations
- [ ] Profile editing and avatar uploads
- [ ] Multiple rooms and room membership
- [ ] Accurate online presence
- [ ] Moderation, rate limiting, and abuse reporting
- [ ] Redis pub/sub for horizontally scaled WebSocket delivery
- [ ] React Native companion client
- [ ] Deployment, monitoring, and screenshots

## Open-source references

This is an independent implementation based on public documentation:

- [React](https://react.dev/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [pwdlib password hashing](https://frankie567.github.io/pwdlib/)
- [PyJWT](https://pyjwt.readthedocs.io/)
- [PostgreSQL](https://www.postgresql.org/docs/)

## License

MIT — see [LICENSE](LICENSE).
