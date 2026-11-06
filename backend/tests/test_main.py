from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def create_account() -> tuple[dict, str]:
    suffix = uuid4().hex[:10]
    response = client.post(
        "/api/auth/register",
        json={
            "username": f"tester_{suffix}",
            "email": f"{suffix}@example.com",
            "password": "a-strong-test-password",
        },
    )
    assert response.status_code == 201
    return response.json(), "a-strong-test-password"


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "community-live-api"}


def test_register_and_read_current_user() -> None:
    account, _ = create_account()
    token = account["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == account["user"]["username"]
    assert response.json()["email"] == account["user"]["email"]


def test_password_is_not_stored_as_plain_text() -> None:
    account, password = create_account()
    from app.database import SessionLocal
    from app.models import User

    with SessionLocal() as session:
        user = session.get(User, account["user"]["id"])
        assert user is not None
        assert user.password_hash != password
        assert user.password_hash.startswith("$argon2")


def test_duplicate_email_or_username_is_rejected() -> None:
    account, _ = create_account()
    duplicate = client.post(
        "/api/auth/register",
        json={
            "username": account["user"]["username"],
            "email": f"other_{uuid4().hex[:8]}@example.com",
            "password": "another-strong-password",
        },
    )
    assert duplicate.status_code == 409


def test_login_returns_access_token() -> None:
    account, password = create_account()
    response = client.post(
        "/api/auth/login",
        json={"email": account["user"]["email"], "password": password},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["id"] == account["user"]["id"]



def test_login_accepts_username() -> None:
    account, password = create_account()
    response = client.post(
        "/api/auth/login",
        json={"email": account["user"]["username"], "password": password},
    )
    assert response.status_code == 200
    assert response.json()["user"]["id"] == account["user"]["id"]

def test_login_rejects_wrong_password() -> None:
    account, _ = create_account()
    response = client.post(
        "/api/auth/login",
        json={"email": account["user"]["email"], "password": "incorrect-password"},
    )
    assert response.status_code == 401


def test_protected_profile_rejects_missing_token() -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_protected_message_history_rejects_missing_token() -> None:
    response = client.get("/api/messages")
    assert response.status_code == 401


def test_authenticated_websocket_persists_and_broadcasts_message() -> None:
    account, _ = create_account()
    token = account["access_token"]
    with client.websocket_connect(f"/ws/chat?token={token}") as websocket:
        websocket.send_json({"text": "Hello, authenticated community!"})
        payload = websocket.receive_json()
        assert payload["type"] == "message"
        assert payload["username"] == account["user"]["username"]
        assert payload["text"] == "Hello, authenticated community!"
        assert isinstance(payload["id"], int)

    history = client.get(
        "/api/messages?limit=100",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history.status_code == 200
    assert any(item["id"] == payload["id"] for item in history.json())


def test_websocket_rejects_invalid_message() -> None:
    account, _ = create_account()
    with client.websocket_connect(f"/ws/chat?token={account['access_token']}") as websocket:
        websocket.send_json({"text": " "})
        payload = websocket.receive_json()
        assert payload["type"] == "error"


def test_websocket_requires_authentication() -> None:
    from fastapi import WebSocketDisconnect
    import pytest

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/chat"):
            pass


def test_message_history_limit_is_validated() -> None:
    account, _ = create_account()
    response = client.get(
        "/api/messages?limit=500",
        headers={"Authorization": f"Bearer {account['access_token']}"},
    )
    assert response.status_code == 422
