from fastapi.testclient import TestClient


def test_health_reports_database_ok(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_unknown_route_uses_standard_error_shape(client: TestClient):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
