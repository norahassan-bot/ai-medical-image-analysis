"""Pytest Test Suite for Task 13: Clinical PDF Report Generation & API Endpoints.

Tests:
1. Report generator initialization and configuration.
2. PDF report generation from SQLite analysis records.
3. PDF file creation, non-empty existence, and valid PDF header (%PDF-).
4. Handling missing analysis records (FileNotFoundError / 404).
5. Graceful handling of missing images or missing Grad-CAM visuals.
6. Safe image path resolution and path-traversal prevention.
7. Report reuse and caching mechanics.
8. FastAPI report endpoint GET /history/{analysis_id}/report.
9. Correct Content-Type (application/pdf) and Content-Disposition headers.
10. Correct safe filename formatting.
"""

import os
import sys
import io
import tempfile
import sqlite3
from pathlib import Path
from uuid import uuid4
import pytest
from PIL import Image as PILImage
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from database.database import initialize_database, create_analysis, get_analysis_by_id
from reports.report_generator import (
    generate_analysis_pdf,
    get_report_path,
    resolve_safe_image_path,
    create_scaled_image,
)
from api.main import app


@pytest.fixture
def temp_environment(tmp_path):
    """Provide isolated temporary database and storage paths for tests."""
    db_file = tmp_path / "test_medical_ai.db"
    storage_dir = tmp_path / "storage"
    reports_dir = tmp_path / "reports_pdf"

    storage_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    initialize_database(db_file)

    old_db = os.environ.get("DATABASE_PATH")
    old_storage = os.environ.get("STORAGE_DIR")
    old_reports = os.environ.get("PDF_REPORTS_DIR")

    os.environ["DATABASE_PATH"] = str(db_file)
    os.environ["STORAGE_DIR"] = str(storage_dir)
    os.environ["PDF_REPORTS_DIR"] = str(reports_dir)

    yield {
        "db_path": db_file,
        "storage_dir": storage_dir,
        "reports_dir": reports_dir,
    }

    if old_db:
        os.environ["DATABASE_PATH"] = old_db
    else:
        os.environ.pop("DATABASE_PATH", None)

    if old_storage:
        os.environ["STORAGE_DIR"] = old_storage
    else:
        os.environ.pop("STORAGE_DIR", None)

    if old_reports:
        os.environ["PDF_REPORTS_DIR"] = old_reports
    else:
        os.environ.pop("PDF_REPORTS_DIR", None)


@pytest.fixture
def sample_analysis_record(temp_environment):
    """Insert a verified sample analysis record with real dummy images."""
    env = temp_environment
    analysis_id = str(uuid4())
    img_dir = env["storage_dir"] / analysis_id
    img_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy PNG images
    orig_path = img_dir / "original.png"
    heat_path = img_dir / "gradcam_heatmap.png"
    over_path = img_dir / "gradcam_overlay.png"

    img = PILImage.new("RGB", (224, 224), color=(100, 100, 100))
    img.save(orig_path)
    img.save(heat_path)
    img.save(over_path)

    record_data = {
        "analysis_id": analysis_id,
        "filename": "test_chest_scan.png",
        "prediction": "PNEUMONIA",
        "predicted_index": 1,
        "confidence": 0.9425,
        "probabilities": {"NORMAL": 0.0575, "PNEUMONIA": 0.9425},
        "model_version": "1.0.0",
        "architecture": "resnet18",
        "device": "cpu",
        "inference_time_ms": 38.45,
        "target_class": "PNEUMONIA",
        "image_reference": f"{analysis_id}/original.png",
        "heatmap_reference": f"{analysis_id}/gradcam_heatmap.png",
        "overlay_reference": f"{analysis_id}/gradcam_overlay.png",
        "original_dimensions": [224, 224],
        "status": "completed",
    }

    saved = create_analysis(record_data, db_path=env["db_path"])
    return saved


def test_report_path_generation(temp_environment):
    """Test sanitized PDF report path generation."""
    env = temp_environment
    path = get_report_path("1234-abcd", output_dir=env["reports_dir"])
    assert path.name == "analysis_1234-abcd.pdf"
    assert path.parent == env["reports_dir"]


def test_report_path_invalid_id():
    """Test report path generation rejects malicious or empty IDs."""
    with pytest.raises(ValueError):
        get_report_path("...///")


def test_safe_image_path_resolution(temp_environment):
    """Test safe image path resolution within storage directory."""
    env = temp_environment
    analysis_id = "test-res-id"
    sub_dir = env["storage_dir"] / analysis_id
    sub_dir.mkdir(parents=True, exist_ok=True)
    test_img = sub_dir / "original.png"
    test_img.write_bytes(b"fakeimagebytes")

    # Safe lookup
    resolved = resolve_safe_image_path(f"{analysis_id}/original.png", storage_base=env["storage_dir"])
    assert resolved is not None
    assert resolved.exists()


def test_safe_image_path_traversal_protection(temp_environment):
    """Test that path traversal attempts are safely rejected."""
    env = temp_environment
    # Attempting to access parent directory
    malicious_ref = "../../../etc/passwd"
    resolved = resolve_safe_image_path(malicious_ref, storage_base=env["storage_dir"])
    assert resolved is None


def test_scaled_image_flowable(temp_environment):
    """Test aspect-ratio image scaling helper."""
    img_path = temp_environment["storage_dir"] / "test_scale.png"
    img = PILImage.new("RGB", (800, 400), color=(50, 50, 50))
    img.save(img_path)

    flowable = create_scaled_image(img_path, max_width=200, max_height=200)
    assert flowable is not None
    # 800x400 scaled into max 200x200 -> 200x100
    assert flowable.drawWidth == 200.0
    assert flowable.drawHeight == 100.0


def test_generate_pdf_success(temp_environment, sample_analysis_record):
    """Test successful PDF report generation from real SQLite record."""
    env = temp_environment
    analysis_id = sample_analysis_record["analysis_id"]

    pdf_path = generate_analysis_pdf(
        analysis_id=analysis_id,
        db_path=env["db_path"],
        output_dir=env["reports_dir"],
    )

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 500  # Non-trivial PDF size

    # Verify standard PDF signature
    with open(pdf_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"


def test_generate_pdf_caching_reuse(temp_environment, sample_analysis_record):
    """Test that existing PDF is reused without rebuilding unless forced."""
    env = temp_environment
    analysis_id = sample_analysis_record["analysis_id"]

    # Initial build
    pdf_path1 = generate_analysis_pdf(
        analysis_id=analysis_id,
        db_path=env["db_path"],
        output_dir=env["reports_dir"],
    )
    mtime1 = pdf_path1.stat().st_mtime

    # Second call without force_regenerate
    pdf_path2 = generate_analysis_pdf(
        analysis_id=analysis_id,
        db_path=env["db_path"],
        output_dir=env["reports_dir"],
        force_regenerate=False,
    )
    mtime2 = pdf_path2.stat().st_mtime

    assert pdf_path1 == pdf_path2
    assert mtime1 == mtime2


def test_generate_pdf_missing_analysis(temp_environment):
    """Test report generation raises FileNotFoundError when record is absent."""
    env = temp_environment
    with pytest.raises(FileNotFoundError):
        generate_analysis_pdf(
            analysis_id="non-existent-uuid",
            db_path=env["db_path"],
            output_dir=env["reports_dir"],
        )


def test_generate_pdf_with_missing_images(temp_environment):
    """Test report generation handles analyses where images were deleted gracefully."""
    env = temp_environment
    analysis_id = str(uuid4())

    record_data = {
        "analysis_id": analysis_id,
        "filename": "missing_img.png",
        "prediction": "NORMAL",
        "predicted_index": 0,
        "confidence": 0.985,
        "probabilities": {"NORMAL": 0.985, "PNEUMONIA": 0.015},
        "model_version": "1.0.0",
        "architecture": "resnet18",
        "device": "cpu",
        "inference_time_ms": 25.1,
        "target_class": "NORMAL",
        "image_reference": "non_existent/orig.png",
        "heatmap_reference": None,
        "overlay_reference": None,
        "status": "completed",
    }
    create_analysis(record_data, db_path=env["db_path"])

    pdf_path = generate_analysis_pdf(
        analysis_id=analysis_id,
        db_path=env["db_path"],
        output_dir=env["reports_dir"],
    )
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0


def test_api_download_report_endpoint(temp_environment, sample_analysis_record):
    """Test FastAPI GET /history/{analysis_id}/report endpoint."""
    analysis_id = sample_analysis_record["analysis_id"]

    with TestClient(app) as client:
        response = client.get(f"/history/{analysis_id}/report")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert f'filename="analysis_{analysis_id}.pdf"' in response.headers.get("content-disposition", "")
        assert response.content.startswith(b"%PDF-")


def test_api_download_report_v1_endpoint(temp_environment, sample_analysis_record):
    """Test FastAPI GET /api/v1/history/{analysis_id}/report alias endpoint."""
    analysis_id = sample_analysis_record["analysis_id"]

    with TestClient(app) as client:
        response = client.get(f"/api/v1/history/{analysis_id}/report")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF-")


def test_api_download_report_not_found(temp_environment):
    """Test FastAPI report endpoint returns 404 for unknown ID."""
    with TestClient(app) as client:
        response = client.get("/history/00000000-0000-0000-0000-000000000000/report")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("detail", "").lower() or "not found" in data.get("error", {}).get("message", "").lower()


def test_api_artifact_endpoint(temp_environment, sample_analysis_record):
    """Test FastAPI GET /history/{analysis_id}/artifacts/{artifact_type} endpoint."""
    analysis_id = sample_analysis_record["analysis_id"]

    with TestClient(app) as client:
        resp_orig = client.get(f"/history/{analysis_id}/artifacts/original")
        assert resp_orig.status_code == 200
        assert resp_orig.headers["content-type"] in ["image/png", "image/jpeg"]

        resp_heat = client.get(f"/history/{analysis_id}/artifacts/heatmap")
        assert resp_heat.status_code == 200

        resp_over = client.get(f"/history/{analysis_id}/artifacts/overlay")
        assert resp_over.status_code == 200
