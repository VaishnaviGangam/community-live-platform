from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "community-live-api",
    }


def test_websocket_persists_and_broadcasts_message() -> None:
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"username": "Vaishnavi", "text": "Hello, community!"})

        payload = websocket.receive_json()

        assert payload["type"] == "message"
        assert payload["username"] == "Vaishnavi"
        assert payload["text"] == "Hello, community!"
        assert isinstance(payload["id"], int)

    history = client.get("/api/messages?limit=100")
    assert history.status_code == 200
    assert any(
        item["id"] == payload["id"] and item["text"] == "Hello, community!"
        for item in history.json()
    )


def test_websocket_rejects_invalid_message() -> None:
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"username": "", "text": " "})

        payload = websocket.receive_json()

        assert payload["type"] == "error"


def test_message_history_limit_is_validated() -> None:
    response = client.get("/api/messages?limit=500")

    assert response.status_code == 422
