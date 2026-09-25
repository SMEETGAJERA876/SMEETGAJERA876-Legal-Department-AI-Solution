from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.api.routes import health as health_route
from app.main import app

client = TestClient(app)


def test_health_ok_when_database_connected(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(health_route, "check_database_connection", lambda: True)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "ClauseLens AI", "database": "connected"}


def test_health_degraded_when_database_unavailable(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(health_route, "check_database_connection", lambda: False)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "unavailable"
