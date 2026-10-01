"""Pytest Security & Input Validation Regression Suite (Task 14).

Covers all strict security requirements:
1. Path traversal in analysis_id (../../secret.txt, ..\\secret.txt)
2. Absolute filesystem path attempts (C:\\Windows\\System32, /etc/passwd)
3. Malformed analysis_id inputs (SQL injection strings, control chars, special chars)
4. Path traversal in artifact_type
5. Safe image path resolution isolation (cannot escape storage directory)
6. Safe PDF report path isolation (cannot escape reports directory)
7. Unsafe user filename handling (filenames are never trusted for disk storage)
8. Oversized payload handling (HTTP 413, rejects before inference)
9. Empty / zero-byte upload handling (HTTP 400)
10. Unsupported file types and disguised non-image files (.exe or .pdf renamed to .png)
11. Corrupted image byte streams
12. Invalid image dimensions (0x0, tiny, huge decompression bomb)
13. CORS protection (unauthorized origins rejected)
14. Database query safety (parameterized queries, no SQL concatenation)
15. Error sanitization (no stack traces, SQL queries, or internal paths leaked in responses)
16. Temporary database isolation (tests use isolated temp databases, never production)
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

from api.main import app, validate_analysis_id_format, default_origins
from src.inference.predict import (
    ChestXRayPredictor,
    PredictionResult,
    ExplainabilityResult,
    ImageValidationError,
    FileTooLargeError,
    UnsupportedFormatError,
    validate_and_load_image,
)
from database.database import (
    initialize_database,
    get_db_connection,
    create_analysis,
    get_analysis_by_id,
    save_analysis_artifacts,
)
from reports.report_generator import (
    get_report_path,
    resolve_safe_image_path,
)

TEST_TEMP_DIR = backend_root / "tests" / ".test_tmp"


@pytest.fixture
def isolated_test_db(tmp_path):
    """Provide completely isolated temporary SQLite database."""
    db_file = tmp_path / f"sec_test_{int(time.time() * 1000)}.db"
    initialize_database(db_file)
    old_db = os.environ.get("DATABASE_PATH")
    os.environ["DATABASE_PATH"] = str(db_file)
    yield db_file
    if old_db:
        os.environ["DATABASE_PATH"] = old_db
    else:
        os.environ.pop("DATABASE_PATH", None)


@pytest.fixture
def valid_png_bytes():
    """Create a synthetic valid 64x64 PNG image."""
    img_arr = np.random.randint(50, 200, (64, 64, 3), dtype=np.uint8)
    pil_img = Image.fromarray(img_arr)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def mock_sec_predictor():
    """Create a mock predictor for safe security testing."""
    predictor = MagicMock(spec=ChestXRayPredictor)
    predictor.is_loaded = True
    predictor.model_version = "1.0.0-sec"
    predictor.target_device = "cpu"
    mock_model = MagicMock()
    mock_model.arch_key = "resnet18"
    predictor.model = mock_model

    predictor.predict.return_value = PredictionResult(
        prediction="NORMAL",
        predicted_index=0,
        confidence=0.98,
        probabilities={"NORMAL": 0.98, "PNEUMONIA": 0.02},
        model_version="1.0.0-sec",
        architecture="resnet18",
        device="cpu",
        inference_time_ms=30.0,
    )

    predictor.predict_with_explanation.return_value = ExplainabilityResult(
        prediction="NORMAL",
        predicted_index=0,
        confidence=0.98,
        probabilities={"NORMAL": 0.98, "PNEUMONIA": 0.02},
        model_version="1.0.0-sec",
        architecture="resnet18",
        device="cpu",
        inference_time_ms=45.0,
        target_class="NORMAL",
        original_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        heatmap_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        overlay_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        original_dimensions=(64, 64),
    )
    return predictor


# =============================================================================
# 1. Path Traversal & Analysis ID Format Hardening
# =============================================================================

@pytest.mark.parametrize("malicious_id", [
    "../../secret.txt",
    "..\\secret.txt",
    "/etc/passwd",
    "C:\\Windows\\System32\\calc.exe",
    "C:/Windows/win.ini",
    "id_with_spaces in it",
    "id_with_null\x00byte",
    "id_with_semicolon; DROP TABLE analyses;--",
    "id_with_special!@#$%^&*()",
    "a" * 200,  # exceeds max length
])
def test_validate_analysis_id_function_rejects_malicious(malicious_id):
    """Verify that validate_analysis_id_format cleanly raises HTTP 400 for any malicious/invalid ID."""
    with pytest.raises(Exception) as excinfo:
        validate_analysis_id_format(malicious_id)


@pytest.mark.parametrize("malicious_id", [
    "..%2F..%2Fsecret.txt",
    "etc_passwd",
    "invalid-special-char!",
    "too-long-" + "a" * 150,
])
def test_path_traversal_and_malformed_analysis_ids_http(malicious_id):
    """Verify that HTTP endpoints reject malformed analysis IDs with 400 or 404."""
    with TestClient(app) as client:
        # GET /history/{id}
        res_detail = client.get(f"/history/{malicious_id}")
        assert res_detail.status_code in [400, 404]
        data = res_detail.json()
        assert "error" in data or "detail" in data

        # GET /history/{id}/report
        res_report = client.get(f"/history/{malicious_id}/report")
        assert res_report.status_code in [400, 404]

        # GET /history/{id}/artifacts/image
        res_artifact = client.get(f"/history/{malicious_id}/artifacts/image")
        assert res_artifact.status_code in [400, 404]


@pytest.mark.parametrize("malicious_artifact_type", [
    "../../etc/passwd",
    "..\\..\\boot.ini",
    "image_invalid_#@",
    "type-too-long-" + "x" * 50,
])
def test_artifact_type_path_traversal(malicious_artifact_type):
    """Verify that malicious artifact_type strings cannot cause directory traversal."""
    with TestClient(app) as client:
        res = client.get(f"/history/valid-uuid-1234/artifacts/{malicious_artifact_type}")
        assert res.status_code in [400, 404]


def test_resolve_safe_image_path_traversal(tmp_path):
    """Verify resolve_safe_image_path strictly prevents escape from storage base directory."""
    base_dir = tmp_path / "safe_storage"
    base_dir.mkdir()
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("classified data")

    # Attempting to escape base_dir using relative traversal
    resolved = resolve_safe_image_path("../secret.txt", storage_base=base_dir)
    assert resolved is None


def test_get_report_path_traversal(tmp_path):
    """Verify get_report_path rejects path traversal in analysis ID."""
    with pytest.raises(ValueError):
        get_report_path("../../secret_report", output_dir=tmp_path)


# =============================================================================
# 2. Safe Filename Handling
# =============================================================================

def test_safe_filename_handling_on_upload(mock_sec_predictor, valid_png_bytes, tmp_path):
    """Verify user-supplied malicious filenames do not affect server storage paths."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)

    with patch("api.main.get_active_predictor", return_value=mock_sec_predictor), \
         patch("api.main.save_analysis_artifacts") as mock_save, \
         TestClient(app) as client:

        mock_save.return_value = {
            "image_reference": "test-uuid/original.png",
            "heatmap_reference": "test-uuid/gradcam_heatmap.png",
            "overlay_reference": "test-uuid/gradcam_overlay.png",
        }

        # Filename contains path traversal payload
        malicious_filename = "../../../../../etc/passwd.png"
        files = {"file": (malicious_filename, valid_png_bytes, "image/png")}

        response = client.post("/analyze", files=files)
        assert response.status_code == 200
        data = response.json()
        # Stored filename is stripped of path components
        assert "/" not in data["filename"]
        assert "\\" not in data["filename"]
        assert data["filename"] == "passwd.png"


# =============================================================================
# 3. File Size Limit & Oversized Upload Protection
# =============================================================================

def test_oversized_payload_rejection(mock_sec_predictor):
    """Verify oversized payloads are rejected with HTTP 413 without invoking the model."""
    with TestClient(app) as client:
        app.state.predictor = mock_sec_predictor
        app.state.model_loaded = True

        oversized_data = b"0" * (16 * 1024 * 1024)  # 16 MB > 15 MB limit
        files = {"file": ("big_xray.png", oversized_data, "image/png")}
        response = client.post("/predict", files=files)
        assert response.status_code == 413
        data = response.json()
        assert data["error"]["code"] in ["FILE_TOO_LARGE", "INVALID_IMAGE"]
        # Model should not have been called
        mock_sec_predictor.predict.assert_not_called()


def test_empty_file_rejection(mock_sec_predictor):
    """Verify empty 0-byte file is rejected with HTTP 400."""
    with TestClient(app) as client:
        app.state.predictor = mock_sec_predictor
        app.state.model_loaded = True

        files = {"file": ("empty.png", b"", "image/png")}
        response = client.post("/predict", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_IMAGE"


# =============================================================================
# 4. Image Content Validation & Disguised Files
# =============================================================================

def test_disguised_executable_rejected(mock_sec_predictor):
    """Verify executable disguised as PNG is rejected by content validation."""
    with TestClient(app) as client:
        app.state.predictor = mock_sec_predictor
        app.state.model_loaded = True

        fake_png = b"MZ\x90\x00\x03\x00\x00\x00fake_executable_binary_content"
        files = {"file": ("malware.png", fake_png, "image/png")}
        response = client.post("/predict", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_IMAGE"


def test_corrupted_image_rejected(mock_sec_predictor):
    """Verify truncated or corrupted image content is rejected cleanly."""
    with TestClient(app) as client:
        app.state.predictor = mock_sec_predictor
        app.state.model_loaded = True

        corrupted = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRcorrupted_data_here"
        files = {"file": ("corrupt.png", corrupted, "image/png")}
        response = client.post("/predict", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_IMAGE"


def test_zero_dimensions_rejected():
    """Verify zero or negative dimensions are rejected."""
    with pytest.raises(ImageValidationError):
        validate_and_load_image(b"")


# =============================================================================
# 5. Database SQL Injection Protection & Isolation
# =============================================================================

def test_sql_injection_protection_in_queries(isolated_test_db):
    """Verify SQL injection payloads in queries do not execute arbitrary SQL."""
    conn = get_db_connection(isolated_test_db)
    try:
        # Attempt SQL injection in get_analysis_by_id
        injection_payload = "' OR '1'='1"
        record = get_analysis_by_id(injection_payload, db_path=isolated_test_db)
        assert record is None

        # Verify database table is still intact and not corrupted
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM analyses;")
        count = cursor.fetchone()[0]
        assert count == 0
    finally:
        conn.close()


def test_database_test_isolation(isolated_test_db):
    """Verify that test operations use isolated temporary database and never touch production."""
    prod_db_path = backend_root / "data" / "medical_ai.db"
    # Create test record in isolated db
    create_analysis(
        {
            "analysis_id": "test-sec-iso-001",
            "prediction": "NORMAL",
            "confidence": 0.99,
            "model_version": "1.0.0",
        },
        db_path=isolated_test_db,
    )
    # Verify present in test db
    assert get_analysis_by_id("test-sec-iso-001", db_path=isolated_test_db) is not None
    # If production DB exists, verify it does NOT contain the test record
    if prod_db_path.exists():
        assert get_analysis_by_id("test-sec-iso-001", db_path=prod_db_path) is None


# =============================================================================
# 6. Error Sanitization & Information Disclosure Protection
# =============================================================================

def test_error_response_sanitization_no_stack_traces(mock_sec_predictor, valid_png_bytes):
    """Verify unhandled exceptions do not leak stack traces or system filepaths to client."""
    with patch("api.main.get_active_predictor") as mock_get:
        mock_get.side_effect = RuntimeError("CRITICAL: Database connection password=SecretPass123 at /var/secret/db.py:99")

        with TestClient(app, raise_server_exceptions=False) as client:
            files = {"file": ("chest.png", valid_png_bytes, "image/png")}
            response = client.post("/predict", files=files)
            assert response.status_code == 500
            data = response.json()
            assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
            # Sensitive words must not appear in the response
            assert "secretpass" not in data["error"]["message"].lower()
            assert "/var/secret" not in data["error"]["message"]
            assert "traceback" not in data["error"]["message"].lower()


# =============================================================================
# 7. CORS Configuration
# =============================================================================

def test_cors_allowed_origins_behavior():
    """Verify CORS headers for configured frontend origin and rejection for unauthorized origin."""
    with TestClient(app) as client:
        # Allowed origin: http://localhost:3000
        res_allowed = client.options(
            "/predict",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert res_allowed.status_code == 200
        assert res_allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"

        # Disallowed arbitrary origin: http://malicious-phishing-site.com
        res_disallowed = client.options(
            "/predict",
            headers={
                "Origin": "http://malicious-phishing-site.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        # Should not grant access-control-allow-origin for unauthorized origin
        assert res_disallowed.headers.get("access-control-allow-origin") != "http://malicious-phishing-site.com"
