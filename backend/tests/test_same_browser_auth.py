import pytest
from fastapi.testclient import TestClient
from api.main import app
from database.database import initialize_database, seed_admin_user
import os

@pytest.fixture
def client():
    return TestClient(app, base_url="http://localhost:8000")

@pytest.fixture(autouse=True)
def setup_db():
    initialize_database()
    seed_admin_user()

def test_user_session_creation(client):
    """Test that visiting /auth/session automatically provisions a USER session."""
    res = client.get("/auth/session")
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "USER"
    assert "user_session_token" in client.cookies
    assert "admin_session_token" not in client.cookies

def test_user_cannot_access_admin_endpoints(client):
    """Test that a USER session is strictly rejected from ADMIN endpoints with 401/403."""
    # 1. Establish USER session
    res = client.get("/auth/session")
    assert res.status_code == 200
    user_cookie = client.cookies["user_session_token"]

    # 2. Try calling admin endpoints with only user cookie
    admin_endpoints = [
        "/admin/statistics",
        "/admin/users",
        "/admin/analyses",
        "/admin/system",
        "/auth/admin/me",
    ]
    for endpoint in admin_endpoints:
        # Create a fresh client with ONLY user cookie to avoid any session carryover
        isolated_client = TestClient(app, base_url="http://localhost:8000")
        isolated_client.cookies.set("user_session_token", user_cookie)
        admin_res = isolated_client.get(endpoint)
        assert admin_res.status_code in [401, 403], f"Endpoint {endpoint} should reject USER session"

def test_same_browser_user_and_admin_coexistence(client):
    """Test that both user_session_token and admin_session_token can coexist in the same browser session."""
    # 1. Establish USER session
    user_res = client.get("/auth/session")
    assert user_res.status_code == 200
    user_token = client.cookies["user_session_token"]

    # 2. Login as ADMIN in the same client
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "AdminSecure2026!Clinical")
    login_res = client.post(
        "/auth/login",
        json={"username": admin_user, "password": admin_pass},
    )
    assert login_res.status_code == 200
    assert "admin_session_token" in client.cookies
    admin_token = client.cookies["admin_session_token"]

    # 3. Verify both cookies are present in client session
    assert "user_session_token" in client.cookies
    assert "admin_session_token" in client.cookies

    # 4. Access admin endpoints with both cookies present -> should succeed
    admin_stats_res = client.get("/admin/statistics")
    assert admin_stats_res.status_code == 200
    assert admin_stats_res.json()["architecture"] is not None

    admin_me_res = client.get("/auth/admin/me")
    assert admin_me_res.status_code == 200
    assert admin_me_res.json()["role"] == "ADMIN"

    # 5. Access user endpoints with both cookies present -> should resolve user profile
    user_me_res = client.get("/auth/me")
    assert user_me_res.status_code == 200
    assert user_me_res.json()["role"] == "USER"

    # 6. Admin logout should clear only admin_session_token
    logout_res = client.post("/auth/admin/logout")
    assert logout_res.status_code == 200
    assert "admin_session_token" not in client.cookies or client.cookies.get("admin_session_token") == ""
    assert "user_session_token" in client.cookies

    # 7. User reset should clear user_session_token
    reset_res = client.post("/auth/session/reset")
    assert reset_res.status_code == 200
    assert "user_session_token" not in client.cookies or client.cookies.get("user_session_token") == ""
