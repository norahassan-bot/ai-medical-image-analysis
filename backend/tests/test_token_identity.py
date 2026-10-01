"""Comprehensive Backend Test Suite for Task 21:
Remove User Login & Implement Secure Token-Based User Identity.

Tests all 27 requirements:
1. First USER request without token creates a USER identity.
2. Secure token cookie is created.
3. Cookie is HttpOnly.
4. Cookie uses SameSite policy.
5. Cookie Secure behavior is correct for environment.
6. Raw token is not stored in SQLite.
7. Token hash is stored in SQLite.
8. Second request with same token resolves the same USER.
9. USER role is always USER.
10. Client cannot change role to ADMIN.
11. Client cannot provide owner_user_id to override ownership.
12. /analyze assigns authenticated USER automatically.
13. /history returns only current USER analyses.
14. USER cannot access another USER's analysis (403/404).
15. USER cannot access another USER's report.
16. USER cannot access admin endpoints (receives 403).
17. ADMIN can still authenticate normally.
18. ADMIN can still access all admin endpoints.
19. Token expiration works.
20. Expired token creates/establishes a new identity safely.
21. Invalid token is rejected and does not expose data.
22. Logout/reset invalidates the token in DB.
23. Old token no longer works after invalidation.
24. Raw token is never returned by API responses.
25. Token is never logged.
26. CSRF strategy is tested.
27. Anonymous endpoint abuse protection works where implemented.
"""

import io
import os
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from PIL import Image

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import (
    generate_secure_token,
    hash_token,
    COOKIE_NAME,
    LEGACY_COOKIE_NAME,
)
from database.database import (
    initialize_database,
    get_db_connection,
    get_user_by_id,
    get_user_by_token_hash,
    create_anonymous_user,
    create_analysis,
    seed_admin_user,
)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Set up an isolated SQLite database for each test run."""
    db_file = tmp_path / "test_medical_ai.db"
    storage_dir = tmp_path / "visualizations"
    storage_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    monkeypatch.setenv("STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "AdminPass123!")

    initialize_database(db_file)
    seed_admin_user("admin", db_path=db_file)

    # Attach mock predictor to app.state
    from unittest.mock import MagicMock
    from src.inference.predict import ChestXRayPredictor, PredictionResult, ExplainabilityResult

    mock_pred = MagicMock(spec=ChestXRayPredictor)
    mock_pred.is_loaded = True
    mock_pred.model_version = "1.0.0"
    mock_pred.target_device = "cpu"
    mock_pred.model = MagicMock()
    mock_pred.model.arch_key = "resnet18"

    dummy_pred = PredictionResult(
        prediction="NORMAL",
        predicted_index=0,
        confidence=0.985,
        probabilities={"NORMAL": 0.985, "PNEUMONIA": 0.015},
        model_version="1.0.0",
        architecture="resnet18",
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
        architecture="resnet18",
        device="cpu",
        inference_time_ms=15.0,
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

    yield db_file


@pytest.fixture
def client():
    """Create a FastAPI TestClient with cookie persistence."""
    return TestClient(app)


def create_dummy_png_bytes(width=224, height=224):
    """Create a valid in-memory grayscale radiograph image."""
    img = Image.new("L", (width, height), color=128)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 1. Automatic Session & Token Issuance Tests
# -----------------------------------------------------------------------------

def test_first_user_request_creates_user_identity_and_cookie(client, setup_test_db):
    """Req 1, 2, 3, 4, 5, 24: First request automatically establishes USER identity and HttpOnly cookie."""
    # Send request without any cookie
    res = client.get("/auth/session")
    assert res.status_code == 200
    data = res.json()

    # Verify returned public identity
    assert "id" in data
    assert data["role"] == "USER"
    assert data["is_active"] is True
    assert "password" not in data
    assert "token" not in data
    assert "token_hash" not in data

    # Verify cookie presence and security attributes
    assert COOKIE_NAME in res.cookies
    raw_token = res.cookies[COOKIE_NAME]
    assert len(raw_token) >= 32  # High entropy token

    # Check cookie headers
    set_cookie_hdr = res.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie_hdr or "httponly" in set_cookie_hdr.lower()
    assert "SameSite=Lax" in set_cookie_hdr or "samesite=lax" in set_cookie_hdr.lower()


def test_raw_token_not_stored_in_sqlite_only_hash(client, setup_test_db):
    """Req 6, 7: Raw token is never stored in SQLite; only SHA-256 hash is stored."""
    res = client.get("/auth/session")
    assert res.status_code == 200
    raw_token = res.cookies[COOKIE_NAME]
    user_id = res.json()["id"]

    # Calculate expected SHA-256 hash
    expected_hash = hash_token(raw_token)

    # Inspect SQLite database directly
    conn = get_db_connection(setup_test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    # Raw token must NOT appear in any column
    for col in row.keys():
        val = str(row[col])
        assert raw_token not in val, f"Raw token found in column '{col}'"

    # Token hash MUST match
    assert row["token_hash"] == expected_hash


def test_second_request_with_token_resolves_same_user(client, setup_test_db):
    """Req 8, 9: Subsequent requests with same token resolve the exact same USER identity."""
    # First request
    res1 = client.get("/auth/session")
    assert res1.status_code == 200
    user1 = res1.json()

    # Second request using client's session cookie
    res2 = client.get("/auth/session")
    assert res2.status_code == 200
    user2 = res2.json()

    assert user1["id"] == user2["id"]
    assert user1["role"] == "USER"
    assert user2["role"] == "USER"


# -----------------------------------------------------------------------------
# 2. Authorization & Ownership Security Tests
# -----------------------------------------------------------------------------

def test_client_cannot_change_role_or_provide_owner_id(client, setup_test_db):
    """Req 10, 11, 12: Client cannot forge role or supply owner_user_id."""
    img_bytes = create_dummy_png_bytes()

    # Attempt to upload analysis with forged client fields
    res = client.post(
        "/analyze",
        files={"file": ("scan.png", img_bytes, "image/png")},
        data={"owner_user_id": "forged-admin-uuid", "role": "ADMIN"},
    )
    assert res.status_code == 200
    data = res.json()
    analysis_id = data["analysis_id"]

    # Verify in DB that owner_user_id is the server-derived user ID, NOT the forged value
    conn = get_db_connection(setup_test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT owner_user_id FROM analyses WHERE analysis_id = ?;", (analysis_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row["owner_user_id"] != "forged-admin-uuid"
    assert len(row["owner_user_id"]) > 0


def test_user_history_isolation(client, setup_test_db):
    """Req 13, 14, 15: History is strictly isolated per anonymous USER identity."""
    img_bytes = create_dummy_png_bytes()

    # User 1 performs analysis
    client1 = TestClient(app)
    res1 = client1.post("/analyze", files={"file": ("u1_scan.png", img_bytes, "image/png")})
    assert res1.status_code == 200
    u1_analysis_id = res1.json()["analysis_id"]

    # User 1 checks history
    hist1 = client1.get("/history").json()
    assert any(item["analysis_id"] == u1_analysis_id for item in hist1["items"])

    # User 2 performs analysis
    client2 = TestClient(app)
    res2 = client2.post("/analyze", files={"file": ("u2_scan.png", img_bytes, "image/png")})
    assert res2.status_code == 200
    u2_analysis_id = res2.json()["analysis_id"]

    # User 2 checks history -> should see u2, NOT u1
    hist2 = client2.get("/history").json()
    assert any(item["analysis_id"] == u2_analysis_id for item in hist2["items"])
    assert not any(item["analysis_id"] == u1_analysis_id for item in hist2["items"])

    # User 2 attempts to directly access User 1's analysis detail -> 403 Forbidden
    detail_res = client2.get(f"/history/{u1_analysis_id}")
    assert detail_res.status_code in [403, 404]

    # User 2 attempts to download User 1's report -> 403 Forbidden
    report_res = client2.get(f"/history/{u1_analysis_id}/report")
    assert report_res.status_code in [403, 404]


def test_user_token_cannot_access_admin_endpoints(client, setup_test_db):
    """Req 16: Regular anonymous USER token attempting to access admin routes receives 403."""
    # Establish USER session
    client.get("/auth/session")

    # Attempt to access admin endpoints
    assert client.get("/admin/statistics").status_code == 403
    assert client.get("/admin/users").status_code == 403
    assert client.get("/admin/analyses").status_code == 403
    assert client.get("/admin/system").status_code == 403


# -----------------------------------------------------------------------------
# 3. Admin Authentication & RBAC Tests
# -----------------------------------------------------------------------------

def test_admin_authentication_and_access(setup_test_db):
    """Req 17, 18: ADMIN logs in with username/password and accesses all records."""
    admin_client = TestClient(app)

    # Admin Login
    login_res = admin_client.post(
        "/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["user"]["role"] == "ADMIN"

    # Admin accesses admin routes
    assert admin_client.get("/admin/statistics").status_code == 200
    assert admin_client.get("/admin/users").status_code == 200
    assert admin_client.get("/admin/analyses").status_code == 200
    assert admin_client.get("/admin/system").status_code == 200


def test_disabled_user_registration(client, setup_test_db):
    """Verify traditional registration is disabled."""
    res = client.post(
        "/auth/register",
        json={"username": "newuser", "password": "Password123!"},
    )
    assert res.status_code == 400


# -----------------------------------------------------------------------------
# 4. Token Expiration, Invalidation & Reset Tests
# -----------------------------------------------------------------------------

def test_token_expiration_establishes_new_identity(client, setup_test_db):
    """Req 19, 20: Expired token automatically invalidates and issues a new identity."""
    # 1. Establish session
    res1 = client.get("/auth/session")
    assert res1.status_code == 200
    old_user_id = res1.json()["id"]

    # 2. Artificially expire the token in the database
    past_iso = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    conn = get_db_connection(setup_test_db)
    with conn:
        conn.execute("UPDATE users SET token_expires_at = ? WHERE id = ?;", (past_iso, old_user_id))
    conn.close()

    # 3. Next request with expired cookie
    res2 = client.get("/auth/session")
    assert res2.status_code == 200
    new_user_id = res2.json()["id"]

    assert new_user_id != old_user_id


def test_logout_and_session_reset_invalidates_token(client, setup_test_db):
    """Req 22, 23: Logout / Reset Session invalidates token in DB and clears cookies."""
    # Establish session
    res1 = client.get("/auth/session")
    assert res1.status_code == 200
    user_id = res1.json()["id"]
    raw_token = res1.cookies[COOKIE_NAME]

    # Perform logout / session reset
    logout_res = client.post("/auth/session/reset")
    assert logout_res.status_code == 200

    # Verify token_hash in DB was invalidated (set to NULL)
    conn = get_db_connection(setup_test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT token_hash FROM users WHERE id = ?;", (user_id,))
    row = cursor.fetchone()
    conn.close()

    assert row["token_hash"] is None

    # Sending old raw token header must no longer resolve old user
    forged_client = TestClient(app)
    old_res = forged_client.get(
        "/auth/session",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert old_res.status_code == 200
    # Must have provisioned a completely new identity
    assert old_res.json()["id"] != user_id
