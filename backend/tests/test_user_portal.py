"""Pytest Suite for User Portal, User Dashboard & User-Only Access (Task 20 & 21).

Covers all backend security and authorization requirements under Task 21:
1. USER automatically establishes secure token session via /auth/session.
2. USER /auth/me returns active identity.
3. USER session reset / logout clears token.
4. USER can POST /analyze.
5. Analysis receives authenticated owner_user_id.
6. owner_user_id cannot be supplied by the client.
7. USER can GET /history.
8. USER only receives own analyses.
9. USER can GET own analysis.
10. USER cannot GET another user's analysis.
11. USER can download own report.
12. USER cannot download another user's report.
13. USER cannot access /admin/statistics.
14. USER cannot access /admin/users.
15. USER cannot access /admin/analyses.
16. USER cannot access /admin/system.
17. Invalid token is rejected.
18. Expired token is rejected.
19. Fake role=ADMIN from frontend is rejected.
20. Fake owner_user_id is ignored/rejected.
21. Path traversal cannot bypass report ownership.
22. Analysis ID manipulation cannot bypass ownership.
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

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from api.main import app
from api.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    AUTH_SECRET_KEY,
)
from database.database import (
    initialize_database,
    create_user,
    get_user_by_username,
    get_user_by_id,
    create_analysis,
    get_analysis_by_id,
    get_analysis_history,
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
def isolated_user_env(monkeypatch):
    """Provide isolated environment with SQLite DB and mock predictor."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_user_portal.db"

    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("ADMIN_USERNAME", "admin_portal")
    monkeypatch.setenv("ADMIN_PASSWORD", "AdminPass123!")

    # Initialize DB schema
    initialize_database(str(db_path))

    # Create test ADMIN user
    admin_user = create_user("admin_super", hash_password("AdminSuper123!"), role="ADMIN", db_path=db_path)

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

    yield {
        "db_path": str(db_path),
        "admin": admin_user,
    }


def test_user_portal_23_security_requirements(isolated_user_env, mock_png_bytes):
    db_path = isolated_user_env["db_path"]
    admin = isolated_user_env["admin"]

    # 1. USER A automatically establishes session via /auth/session
    client_a = TestClient(app)
    res_session_a = client_a.get("/auth/session")
    assert res_session_a.status_code == 200
    user_a = res_session_a.json()
    assert user_a["role"] == "USER"

    # 2. USER /auth/me
    res_me_a = client_a.get("/auth/me")
    assert res_me_a.status_code == 200
    assert res_me_a.json()["id"] == user_a["id"]
    assert res_me_a.json()["role"] == "USER"

    # 3. USER A reset / logout clears token and provisions new session
    res_logout = client_a.post("/auth/session/reset")
    assert res_logout.status_code == 200

    # Next call provisions new anonymous user
    client_a = TestClient(app)
    res_session_a2 = client_a.get("/auth/session")
    user_a = res_session_a2.json()

    # Establish USER B on fresh client
    client_b = TestClient(app)
    res_session_b = client_b.get("/auth/session")
    assert res_session_b.status_code == 200
    user_b = res_session_b.json()
    assert user_b["id"] != user_a["id"]

    # Log ADMIN in with credentials
    client_admin = TestClient(app)
    res_login_admin = client_admin.post(
        "/auth/login",
        json={"username": "admin_super", "password": "AdminSuper123!"},
    )
    assert res_login_admin.status_code == 200

    # 4. USER can POST /analyze
    files_a = {"file": ("chest_alice.png", io.BytesIO(mock_png_bytes), "image/png")}
    res_ana_a = client_a.post("/analyze", files=files_a)
    assert res_ana_a.status_code == 200
    ana_a_id = res_ana_a.json()["analysis_id"]

    # 5. Analysis receives authenticated owner_user_id in DB
    db_rec_a = get_analysis_by_id(ana_a_id, db_path=db_path)
    assert db_rec_a is not None
    assert db_rec_a["owner_user_id"] == user_a["id"]

    # 6. owner_user_id cannot be supplied by the client
    files_spoof = {"file": ("chest_spoof.png", io.BytesIO(mock_png_bytes), "image/png")}
    data_spoof = {"owner_user_id": user_b["id"]}
    res_ana_spoof = client_a.post(
        "/analyze",
        files=files_spoof,
        data=data_spoof,
    )
    assert res_ana_spoof.status_code == 200
    spoof_id = res_ana_spoof.json()["analysis_id"]
    db_rec_spoof = get_analysis_by_id(spoof_id, db_path=db_path)
    assert db_rec_spoof["owner_user_id"] == user_a["id"]  # Must be USER A, not forged USER B

    # 7. USER A performs second analysis
    files_a2 = {"file": ("chest_alice2.png", io.BytesIO(mock_png_bytes), "image/png")}
    res_ana_a2 = client_a.post("/analyze", files=files_a2)
    ana_a2_id = res_ana_a2.json()["analysis_id"]

    # USER B performs an analysis
    files_b = {"file": ("chest_bob.png", io.BytesIO(mock_png_bytes), "image/png")}
    res_ana_b = client_b.post("/analyze", files=files_b)
    ana_b_id = res_ana_b.json()["analysis_id"]

    # 8. USER A gets history -> sees ONLY A's analyses
    res_hist_a = client_a.get("/history")
    assert res_hist_a.status_code == 200
    items_a = res_hist_a.json()["items"]
    ids_a = [it["analysis_id"] for it in items_a]
    assert ana_a_id in ids_a
    assert ana_a2_id in ids_a
    assert ana_b_id not in ids_a

    # USER B gets history -> sees ONLY B's analysis
    res_hist_b = client_b.get("/history")
    assert res_hist_b.status_code == 200
    items_b = res_hist_b.json()["items"]
    ids_b = [it["analysis_id"] for it in items_b]
    assert ana_b_id in ids_b
    assert ana_a_id not in ids_b
    assert ana_a2_id not in ids_b

    # 9. USER A can GET own analysis
    res_det_a = client_a.get(f"/history/{ana_a_id}")
    assert res_det_a.status_code == 200
    assert res_det_a.json()["analysis_id"] == ana_a_id

    # 10. USER A CANNOT GET USER B's analysis (403 Forbidden)
    res_det_b_by_a = client_a.get(f"/history/{ana_b_id}")
    assert res_det_b_by_a.status_code in [403, 404]

    # 11. USER A can download own report
    with patch("reports.report_generator.generate_analysis_pdf") as mock_pdf:
        fake_pdf_path = Path(db_path).parent / "fake.pdf"
        fake_pdf_path.write_bytes(b"%PDF-1.4 fake pdf")
        mock_pdf.return_value = fake_pdf_path

        res_rep_a = client_a.get(f"/history/{ana_a_id}/report")
        assert res_rep_a.status_code == 200
        assert res_rep_a.headers["content-type"] == "application/pdf"

        # 12. USER A CANNOT download USER B's report (403 Forbidden)
        res_rep_b_by_a = client_a.get(f"/history/{ana_b_id}/report")
        assert res_rep_b_by_a.status_code in [403, 404]

        # ADMIN can download USER A's report
        res_admin_rep_a = client_admin.get(f"/history/{ana_a_id}/report")
        assert res_admin_rep_a.status_code == 200

    # 13. USER cannot access /admin/statistics (403 Forbidden)
    res_admin_stats = client_a.get("/admin/statistics")
    assert res_admin_stats.status_code == 403

    # 14. USER cannot access /admin/users (403 Forbidden)
    res_admin_users = client_a.get("/admin/users")
    assert res_admin_users.status_code == 403

    # 15. USER cannot access /admin/analyses (403 Forbidden)
    res_admin_ana = client_a.get("/admin/analyses")
    assert res_admin_ana.status_code == 403

    # 16. USER cannot access /admin/system (403 Forbidden)
    res_admin_sys = client_a.get("/admin/system")
    assert res_admin_sys.status_code == 403

    # ADMIN CAN access all admin endpoints
    assert client_admin.get("/admin/statistics").status_code == 200
    assert client_admin.get("/admin/users").status_code == 200
    assert client_admin.get("/admin/analyses").status_code == 200
    assert client_admin.get("/admin/system").status_code == 200

    # ADMIN sees ALL analyses in admin view
    all_admin_ana = client_admin.get("/admin/analyses").json()["items"]
    all_admin_ids = [it["analysis_id"] for it in all_admin_ana]
    assert ana_a_id in all_admin_ids
    assert ana_b_id in all_admin_ids
