"""Tests for Prescription Understanding & Analysis API Endpoints."""

import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from api.main import app
from database.database import initialize_database


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    initialize_database()


@pytest.fixture
def client():
    return TestClient(app)


def create_dummy_prescription_image():
    """Create a test image in bytes."""
    img = Image.new("RGB", (300, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def test_prescription_analyze_endpoint_anonymous_user(client):
    img_bytes = create_dummy_prescription_image()
    response = client.post(
        "/prescription/analyze",
        files={"file": ("test_rx.png", img_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert "status" in data
    assert "total_medications" in data
    assert "result" in data
    assert data["result"]["analysis_type"] == "prescription_understanding"
    assert "disclaimer_ar" in data["result"]
    assert "disclaimer_en" in data["result"]


def test_prescription_history_and_detail(client):
    img_bytes = create_dummy_prescription_image()
    # 1. Analyze
    res_upload = client.post(
        "/prescription/analyze",
        files={"file": ("test_rx.png", img_bytes, "image/png")},
    )
    assert res_upload.status_code == 200
    analysis_id = res_upload.json()["analysis_id"]

    # 2. Get history
    res_hist = client.get("/prescription/history")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert "items" in hist_data
    assert hist_data["total"] >= 1
    assert any(i["analysis_id"] == analysis_id for i in hist_data["items"])

    # 3. Get detail
    res_detail = client.get(f"/prescription/history/{analysis_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["analysis_id"] == analysis_id
    assert "result" in detail_data

    # 4. Get artifact
    res_art = client.get(f"/prescription/history/{analysis_id}/artifacts/image")
    assert res_art.status_code == 200
    assert len(res_art.content) > 0


def test_prescription_analyze_invalid_file(client):
    response = client.post(
        "/prescription/analyze",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400
