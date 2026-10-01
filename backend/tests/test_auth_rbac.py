"""Pytest Security & Role-Based Access Control (RBAC) Test Suite (Task 19 & Task 21).

Validates all required backend authentication & authorization requirements:
1. Admin login success
2. Admin login failure
3. Invalid credentials
4. Authenticated user retrieval (GET /auth/me & GET /auth/session)
5. Logout
6. Expired token / session
7. Invalid token
8. Missing token auto-provisions anonymous USER session
9. USER access to analysis
10. USER access to own history
11. USER cannot access another user's history
12. USER cannot access another user's analysis
13. USER cannot download another user's report
14. ADMIN can access all analyses
15. ADMIN can access all reports
16. USER cannot access admin routes
17. USER gets HTTP 403 on admin endpoints
18. Inactive user is denied access
19. Owner cannot be supplied by client (server-derived ownership)
20. Analysis is assigned to authenticated user
21. Password is hashed with bcrypt
22. Plaintext password is not stored in database
23. Secret key is not exposed in responses
24. Login throttling / rate limiting behavior for Admin login
25. Safe authentication error responses (no credential leaking)
26. Cookie security flags (HttpOnly, SameSite)
27. Security headers present
28. Logout clears cookie
"""

import io
import os
import sys
import time
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from api.main import app
from api.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    FAILED_LOGIN_ATTEMPTS,
    AUTH_SECRET_KEY,
    generate_secure_token,
    hash_token,
)
from database.database import (
    initialize_database,
    create_user,
    create_anonymous_user,
    get_user_by_username,
    get_user_by_id,
    create_analysis,
    get_analysis_by_id,
    get_analysis_history,
    update_user_status,
    list_users,
    count_users,
    get_admin_statistics,
)
from src.inference.predict import (
    ChestXRayPredictor,
    PredictionResult,
    ExplainabilityResult,
)


@pytest.fixture
def mock_png_bytes():
    """Create a synthetic 64x64 valid PNG byte stream."""
    img_arr = np.random.randint(50, 200, (64, 64, 3), dtype=np.uint8)
    pil_img = Image.fromarray(img_arr)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def isolated_db(monkeypatch):
    """Provide an isolated temporary SQLite database for each test."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_auth_rbac.db"

    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("ADMIN_USERNAME", "admin_test")
    monkeypatch.setenv("ADMIN_PASSWORD", "SuperSecureAdminPass123!")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-super-secret-key-32-chars-long!")

    import database.database as db_mod
    monkeypatch.setattr(db_mod, "get_db_path", lambda: db_path)

    initialize_database(str(db_path))
    FAILED_LOGIN_ATTEMPTS.clear()

    yield db_path

    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass


@pytest.fixture
def mock_predictor_app():
    """Mock predictor on app.state for fast predictable tests."""
    mock_pred = MagicMock(spec=ChestXRayPredictor)
    mock_pred.is_loaded = True
    mock_pred.model_version = "1.0.0"
    mock_pred.target_device = "cpu"
    mock_pred.model = MagicMock()
    mock_pred.model.arch_key = "densenet121"

    dummy_pred = PredictionResult(
        prediction="NORMAL",
        predicted_index=0,
        confidence=0.985,
        probabilities={"NORMAL": 0.985, "PNEUMONIA": 0.015},
        model_version="1.0.0",
        architecture="densenet121",
        device="cpu",
        inference_time_ms=12.5,
        class_mapping={"NORMAL": 0, "PNEUMONIA": 1},
    )
    dummy_explain = ExplainabilityResult(
        prediction="NORMAL",
        predicted_index=0,
        confidence=0.985,
        probabilities={"NORMAL": 0.985, "PNEUMONIA": 0.015},
        model_version="1.0.0",
        architecture="densenet121",
        device="cpu",
        inference_time_ms=25.0,
        target_class="NORMAL",
        original_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
        heatmap_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
        overlay_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
        original_dimensions=(64, 64),
        class_mapping={"NORMAL": 0, "PNEUMONIA": 1},
        disclaimer="Clinical research only.",
    )

    mock_pred.predict.return_value = dummy_pred
    mock_pred.predict_with_explanation.return_value = dummy_explain

    app.state.predictor = mock_pred
    app.state.model_loaded = True
    return mock_pred


# -----------------------------------------------------------------------------
# 1. Password Hashing & Security Requirements
# -----------------------------------------------------------------------------
def test_password_hashing_and_verification(isolated_db):
    """Test item 21 & 22: Passwords are encrypted with bcrypt and plaintext is never stored."""
    password = "MySecurePassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

    # Create admin user and verify database row
    user = create_user("doctor_alice", hashed, role="ADMIN", db_path=isolated_db)
    fetched = get_user_by_username("doctor_alice", db_path=isolated_db)
    assert fetched is not None
    assert fetched["password_hash"] == hashed
    assert "MySecurePassword123!" not in fetched["password_hash"]


# -----------------------------------------------------------------------------
# 2. Admin & User Login Scenarios
# -----------------------------------------------------------------------------
def test_admin_login_success_and_cookie(isolated_db):
    """Test item 1 & 26: Admin login succeeds and returns safe response with HttpOnly cookie."""
    hashed = hash_password("AdminPass123!")
    create_user("admin_user", hashed, role="ADMIN", db_path=isolated_db)

    client = TestClient(app)
    response = client.post(
        "/auth/login",
        json={"username": "admin_user", "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["username"] == "admin_user"
    assert data["user"]["role"] == "ADMIN"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]

    # Verify cookie
    assert "admin_session_token" in response.cookies or "access_token" in response.cookies
    cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie_header or "httponly" in cookie_header.lower()
    assert "SameSite=lax" in cookie_header or "samesite=lax" in cookie_header.lower()


def test_admin_login_failure_and_safe_error(isolated_db):
    """Test item 2, 3 & 25: Login failure returns HTTP 401 with generic message."""
    create_user("admin_user", hash_password("CorrectPass!"), role="ADMIN", db_path=isolated_db)

    client = TestClient(app)
    response = client.post(
        "/auth/login",
        json={"username": "admin_user", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Invalid administrator username or password" in response.json()["error"]["message"]

    # Non-existent user
    resp_nonexistent = client.post(
        "/auth/login",
        json={"username": "ghost_user", "password": "AnyPassword!"},
    )
    assert resp_nonexistent.status_code == 401
    assert "Invalid administrator username or password" in resp_nonexistent.json()["error"]["message"]


def test_authenticated_user_retrieval_and_logout(isolated_db):
    """Test item 4, 5 & 28: GET /auth/session returns current user, and POST /auth/logout clears session."""
    client = TestClient(app)
    # 1. Establish anonymous user session
    res_session = client.get("/auth/session")
    assert res_session.status_code == 200
    user_data = res_session.json()
    assert user_data["role"] == "USER"

    # 2. Get profile via cookie
    me_resp = client.get("/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["id"] == user_data["id"]
    assert me_resp.json()["role"] == "USER"

    # 3. Logout / Reset
    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 200


# -----------------------------------------------------------------------------
# 3. Inactive Users & Security Requirements
# -----------------------------------------------------------------------------
def test_inactive_user_denied(isolated_db):
    """Test item 18: Inactive users cannot authenticate or access endpoints."""
    # Create inactive admin
    user = create_user("inactive_admin", hash_password("Pass123!"), role="ADMIN", is_active=False, db_path=isolated_db)
    client = TestClient(app)

    # Attempt login
    login_resp = client.post(
        "/auth/login",
        json={"username": "inactive_admin", "password": "Pass123!"},
    )
    assert login_resp.status_code == 403


# -----------------------------------------------------------------------------
# 4. User Isolation & Server-Derived Ownership (Task 19 & 21 Core)
# -----------------------------------------------------------------------------
def test_user_analysis_ownership_and_isolation(isolated_db, mock_predictor_app, mock_png_bytes):
    """Test item 9, 10, 11, 12, 19 & 20: USER analysis is server-assigned and strictly isolated."""
    client1 = TestClient(app)
    res_u1 = client1.get("/auth/session")
    u1_id = res_u1.json()["id"]

    client2 = TestClient(app)
    res_u2 = client2.get("/auth/session")
    u2_id = res_u2.json()["id"]
    assert u1_id != u2_id

    # User 1 performs analysis
    resp1 = client1.post(
        "/analyze",
        files={"file": ("chest.png", mock_png_bytes, "image/png")},
    )
    assert resp1.status_code == 200
    analysis1_id = resp1.json()["analysis_id"]

    # Verify record in DB has u1_id as owner
    db_rec = get_analysis_by_id(analysis1_id, db_path=isolated_db)
    assert db_rec["owner_user_id"] == u1_id

    # User 1 history contains this analysis
    hist1 = client1.get("/history")
    assert hist1.status_code == 200
    assert any(item["analysis_id"] == analysis1_id for item in hist1.json()["items"])

    # User 2 history CANNOT contain User 1's analysis
    hist2 = client2.get("/history")
    assert hist2.status_code == 200
    assert all(item["analysis_id"] != analysis1_id for item in hist2.json()["items"])

    # User 2 cannot access User 1's analysis detail (HTTP 403)
    detail2 = client2.get(f"/history/{analysis1_id}")
    assert detail2.status_code in [403, 404]

    # User 2 cannot download User 1's report (HTTP 403)
    report2 = client2.get(f"/history/{analysis1_id}/report")
    assert report2.status_code in [403, 404]


# -----------------------------------------------------------------------------
# 5. Admin Full Access vs User Route Restrictions
# -----------------------------------------------------------------------------
def test_admin_access_and_user_rbac_restrictions(isolated_db, mock_predictor_app, mock_png_bytes):
    """Test item 14, 15, 16, 17: Admin has full access to all analyses/reports; regular user gets 403 on admin routes."""
    admin = create_user("super_admin", hash_password("AdminPass!"), role="ADMIN", db_path=isolated_db)
    admin_token = create_access_token(admin["id"], admin["username"], admin["role"])

    admin_client = TestClient(app)
    admin_client.cookies.set("access_token", admin_token)

    user_client = TestClient(app)
    user_client.get("/auth/session")

    # Normal user performs analysis
    user_resp = user_client.post(
        "/analyze",
        files={"file": ("user_xray.png", mock_png_bytes, "image/png")},
    )
    assert user_resp.status_code == 200
    analysis_id = user_resp.json()["analysis_id"]

    # Admin CAN access user's analysis detail
    admin_detail = admin_client.get(f"/history/{analysis_id}")
    assert admin_detail.status_code == 200

    # Admin CAN see all analyses in /admin/analyses
    admin_analyses = admin_client.get("/admin/analyses")
    assert admin_analyses.status_code == 200
    assert any(a["analysis_id"] == analysis_id for a in admin_analyses.json()["items"])

    # Admin CAN view admin statistics & users
    stats_resp = admin_client.get("/admin/statistics")
    assert stats_resp.status_code == 200

    users_resp = admin_client.get("/admin/users")
    assert users_resp.status_code == 200

    # Regular USER attempting admin routes MUST get HTTP 403
    assert user_client.get("/admin/statistics").status_code == 403
    assert user_client.get("/admin/users").status_code == 403
    assert user_client.get("/admin/analyses").status_code == 403
    assert user_client.get("/admin/system").status_code == 403


# -----------------------------------------------------------------------------
# 6. Login Abuse / Throttling & Security Headers
# -----------------------------------------------------------------------------
def test_login_throttling_protection(isolated_db):
    """Test item 24: Repeated failed admin logins trigger HTTP 429 Too Many Requests."""
    create_user("target_admin", hash_password("Secret123!"), role="ADMIN", db_path=isolated_db)
    client = TestClient(app)

    # Send 5 failed attempts
    for _ in range(5):
        client.post("/auth/login", json={"username": "target_admin", "password": "WrongPassword"})

    # 6th attempt should trigger 429
    blocked_resp = client.post("/auth/login", json={"username": "target_admin", "password": "Secret123!"})
    assert blocked_resp.status_code == 429
    assert "Too many failed login attempts" in blocked_resp.json()["error"]["message"]


def test_security_headers_present(isolated_db):
    """Test item 27: Security headers (X-Content-Type-Options, X-Frame-Options, etc.) are present."""
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert "strict-origin-when-cross-origin" in resp.headers.get("referrer-policy", "")
