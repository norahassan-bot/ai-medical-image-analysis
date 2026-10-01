from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_get_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert isinstance(data["model_loaded"], bool)


def test_get_api_v1_health():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert isinstance(data["model_loaded"], bool)


def test_get_system_info():
    with TestClient(app) as client:
        response = client.get("/api/v1/system/info")
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "docs_url" in data
