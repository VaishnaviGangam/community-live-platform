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


def test_websocket_broadcasts_message_to_sender() -> None:
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"username": "Vaishnavi", "text": "Hello, community!"})

        payload = websocket.receive_json()

        assert payload == {
            "type": "message",
            "username": "Vaishnavi",
            "text": "Hello, community!",
        }


def test_websocket_rejects_invalid_message() -> None:
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"username": "", "text": " "})

        payload = websocket.receive_json()

        assert payload["type"] == "error"
