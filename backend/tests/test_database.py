"""Pytest suite for SQLite Analysis History & Persistence (Task 10).

Validates:
1. Database initialization.
2. Table creation.
3. Analysis creation.
4. Unique analysis ID.
5. Timestamp creation.
6. Stored prediction.
7. Stored confidence.
8. Stored model version.
9. Stored image references.
10. Retrieve analysis by ID.
11. Missing analysis handling.
12. History retrieval.
13. Newest-first ordering.
14. History limits/pagination.
15. Count analyses.
16. SQL parameterization/safe queries.
17. Database error handling.
18. API /analyze persistence.
19. API /history.
20. API /history/{analysis_id}.
"""

import os
import io
import sys
import time
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock
import numpy as np
from PIL import Image
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from database.database import (
    initialize_database,
    get_db_connection,
    create_analysis,
    get_analysis_by_id,
    get_analysis_history,
    count_analyses,
    delete_analysis,
    save_analysis_artifacts,
)
from api.main import app
from src.inference.predict import (
    ChestXRayPredictor,
    ExplainabilityResult,
)

TEST_TEMP_DIR = backend_root / "tests" / ".test_tmp"


@pytest.fixture
def test_db_path(tmp_path_factory):
    """Provide a dedicated temporary SQLite database path on E: drive."""
    TEST_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    db_file = TEST_TEMP_DIR / f"test_medical_{int(time.time() * 1000)}.db"
    initialize_database(db_file)
    yield db_file
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass


@pytest.fixture
def sample_analysis_payload():
    return {
        "filename": "chest_xray_01.png",
        "prediction": "PNEUMONIA",
        "predicted_index": 1,
        "confidence": 0.942,
        "probabilities": {"NORMAL": 0.058, "PNEUMONIA": 0.942},
        "model_version": "1.0.0",
        "architecture": "resnet18",
        "device": "cpu",
        "inference_time_ms": 42.5,
        "target_class": "PNEUMONIA",
        "image_reference": "sample_uuid/original.png",
        "heatmap_reference": "sample_uuid/gradcam_heatmap.png",
        "overlay_reference": "sample_uuid/gradcam_overlay.png",
        "original_dimensions": [1024, 768],
        "status": "completed",
    }


# 1. Database initialization & 2. Table creation
def test_database_initialization_and_table_creation(test_db_path):
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analyses';")
    table = cursor.fetchone()
    conn.close()
    assert table is not None
    assert table[0] == "analyses"


# 3. Analysis creation & 4. Unique ID & 5. Timestamp & 6. Prediction & 7. Confidence & 8. Model version
def test_create_analysis_fields(test_db_path, sample_analysis_payload):
    record = create_analysis(sample_analysis_payload, db_path=test_db_path)

    assert "analysis_id" in record
    assert len(record["analysis_id"]) > 10  # Valid UUID
    assert "created_at" in record
    assert record["prediction"] == "PNEUMONIA"
    assert record["confidence"] == 0.942
    assert record["model_version"] == "1.0.0"
    assert record["probabilities"]["PNEUMONIA"] == 0.942
    assert record["original_dimensions"] == [1024, 768]


# 9. Stored image references & artifact saving
def test_artifact_saving(tmp_path):
    storage_dir = TEST_TEMP_DIR / "visualizations"
    dummy_bytes = b"FAKE_PNG_BYTES_FOR_TEST"
    dummy_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    refs = save_analysis_artifacts(
        analysis_id="test_uuid_123",
        original_bytes=dummy_bytes,
        original_filename="sample.png",
        heatmap_base64=dummy_b64,
        overlay_base64=dummy_b64,
        storage_dir=storage_dir,
    )
    assert refs["image_reference"] == "test_uuid_123/original.png"
    assert refs["heatmap_reference"] == "test_uuid_123/gradcam_heatmap.png"
    assert refs["overlay_reference"] == "test_uuid_123/gradcam_overlay.png"

    assert (storage_dir / "test_uuid_123" / "original.png").exists()
    assert (storage_dir / "test_uuid_123" / "gradcam_heatmap.png").exists()


# 10. Retrieve analysis by ID
def test_get_analysis_by_id(test_db_path, sample_analysis_payload):
    created = create_analysis(sample_analysis_payload, db_path=test_db_path)
    fetched = get_analysis_by_id(created["analysis_id"], db_path=test_db_path)

    assert fetched is not None
    assert fetched["analysis_id"] == created["analysis_id"]
    assert fetched["prediction"] == "PNEUMONIA"
    assert fetched["confidence"] == 0.942
    assert fetched["probabilities"] == {"NORMAL": 0.058, "PNEUMONIA": 0.942}


# 11. Missing analysis handling
def test_get_missing_analysis_handling(test_db_path):
    fetched = get_analysis_by_id("non_existent_uuid_99999", db_path=test_db_path)
    assert fetched is None


# 12. History retrieval & 13. Newest-first ordering & 14. Limits/pagination & 15. Count analyses
def test_history_ordering_and_pagination(test_db_path):
    for i in range(5):
        create_analysis(
            {
                "prediction": "NORMAL" if i % 2 == 0 else "PNEUMONIA",
                "confidence": 0.90 + i * 0.01,
                "model_version": "1.0.0",
                "created_at": f"2026-09-29T10:0{i}:00Z",
            },
            db_path=test_db_path,
        )

    assert count_analyses(db_path=test_db_path) == 5

    # Page 1: limit 2
    items_p1, total = get_analysis_history(limit=2, offset=0, db_path=test_db_path)
    assert total == 5
    assert len(items_p1) == 2
    # Newest timestamp should come first
    assert items_p1[0]["created_at"] == "2026-09-29T10:04:00Z"
    assert items_p1[1]["created_at"] == "2026-09-29T10:03:00Z"

    # Page 2: limit 2 offset 2
    items_p2, _ = get_analysis_history(limit=2, offset=2, db_path=test_db_path)
    assert len(items_p2) == 2
    assert items_p2[0]["created_at"] == "2026-09-29T10:02:00Z"


# 16. SQL Parameterization / Safe Queries
def test_sql_parameterization(test_db_path):
    injection_id = "'; DROP TABLE analyses; --"
    # Query with malicious string
    res = get_analysis_by_id(injection_id, db_path=test_db_path)
    assert res is None

    # Verify table still intact
    assert count_analyses(db_path=test_db_path) == 0


# 17. Database error handling
def test_database_error_handling():
    # Attempt connecting to an invalid path or invalid read
    with pytest.raises(Exception):
        create_analysis({}, db_path="Z:/invalid_non_existent_drive/test.db")


# 18. API /analyze persistence & 19. API /history & 20. API /history/{analysis_id}
def test_api_analyze_and_history_integration(test_db_path, monkeypatch):
    # Route database calls to test_db_path
    monkeypatch.setenv("DATABASE_PATH", str(test_db_path))

    # Mock predictor
    mock_predictor = MagicMock(spec=ChestXRayPredictor)
    mock_predictor.is_loaded = True
    mock_predictor.model_version = "1.0.0"
    mock_predictor.target_device = "cpu"
    mock_model = MagicMock()
    mock_model.arch_key = "resnet18"
    mock_predictor.model = mock_model

    mock_predictor.predict_with_explanation.return_value = ExplainabilityResult(
        prediction="NORMAL",
        predicted_index=0,
        confidence=0.965,
        probabilities={"NORMAL": 0.965, "PNEUMONIA": 0.035},
        model_version="1.0.0",
        architecture="resnet18",
        device="cpu",
        inference_time_ms=50.0,
        target_class="NORMAL",
        original_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        heatmap_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        overlay_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        original_dimensions=(64, 64),
    )

    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        # Generate synthetic image
        img_arr = np.random.randint(50, 200, (64, 64, 3), dtype=np.uint8)
        pil_img = Image.fromarray(img_arr)
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        buf.seek(0)

        # 18. POST /analyze
        files = {"file": ("normal_scan.png", buf.getvalue(), "image/png")}
        resp_analyze = client.post("/analyze", files=files)
        assert resp_analyze.status_code == 200
        data_analyze = resp_analyze.json()

        analysis_id = data_analyze["analysis_id"]
        assert analysis_id is not None
        assert data_analyze["prediction"] == "NORMAL"
        assert data_analyze["confidence"] == 0.965

        # 19. GET /history
        resp_history = client.get("/history")
        assert resp_history.status_code == 200
        data_history = resp_history.json()
        assert data_history["total"] >= 1
        assert any(item["analysis_id"] == analysis_id for item in data_history["items"])

        # 20. GET /history/{analysis_id}
        resp_detail = client.get(f"/history/{analysis_id}")
        assert resp_detail.status_code == 200
        data_detail = resp_detail.json()
        assert data_detail["analysis_id"] == analysis_id
        assert data_detail["prediction"] == "NORMAL"
        assert data_detail["confidence"] == 0.965

        # 21. GET /history/invalid_id returns 404
        resp_404 = client.get("/history/non-existent-uuid")
        assert resp_404.status_code == 404
        assert resp_404.json()["error"]["code"] == "NOT_FOUND"
