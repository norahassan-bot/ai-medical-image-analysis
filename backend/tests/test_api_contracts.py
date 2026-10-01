"""Integration Contract Tests for Next.js <-> FastAPI compatibility (Task 12).

Verifies:
1. GET /health contract matches HealthResponse schema.
2. POST /analyze contract matches AnalysisResponse schema.
3. GET /history contract matches AnalysisHistoryResponse schema.
4. GET /history/{analysis_id} contract matches AnalysisDetailResponse schema.
5. Error structure matches ErrorResponse schema.
6. CORS headers permit http://localhost:3000.
"""

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock
import numpy as np
from PIL import Image
import pytest
from fastapi.testclient import TestClient

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from api.main import app
from src.inference.predict import (
    ChestXRayPredictor,
    ExplainabilityResult,
)


@pytest.fixture
def dummy_png_bytes():
    arr = np.random.randint(50, 200, (64, 64, 3), dtype=np.uint8)
    pil_img = Image.fromarray(arr)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def mock_predictor():
    predictor = MagicMock(spec=ChestXRayPredictor)
    predictor.is_loaded = True
    predictor.model_version = "1.0.0"
    predictor.target_device = "cpu"
    mock_model = MagicMock()
    mock_model.arch_key = "resnet18"
    predictor.model = mock_model

    predictor.predict_with_explanation.return_value = ExplainabilityResult(
        prediction="NORMAL",
        predicted_index=0,
        confidence=0.954,
        probabilities={"NORMAL": 0.954, "PNEUMONIA": 0.046},
        model_version="1.0.0",
        architecture="resnet18",
        device="cpu",
        inference_time_ms=48.2,
        target_class="NORMAL",
        original_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        heatmap_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        overlay_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        original_dimensions=(64, 64),
    )
    return predictor


# 1. Health Contract
def test_health_contract(mock_predictor):
    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()

        # TypeScript HealthResponse contract
        assert isinstance(data["status"], str)
        assert isinstance(data["model_loaded"], bool)
        assert "model_version" in data
        assert "architecture" in data
        assert "device" in data


# 2. Analyze Contract
def test_analyze_contract(mock_predictor, dummy_png_bytes):
    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        files = {"file": ("chest.png", dummy_png_bytes, "image/png")}
        res = client.post("/analyze", files=files)
        assert res.status_code == 200
        data = res.json()

        # TypeScript AnalysisResponse contract
        assert isinstance(data["analysis_id"], str)
        assert isinstance(data["created_at"], str)
        assert data["prediction"] in ["NORMAL", "PNEUMONIA"]
        assert isinstance(data["predicted_index"], int)
        assert isinstance(data["confidence"], float)
        assert isinstance(data["probabilities"], dict)
        assert "NORMAL" in data["probabilities"]
        assert "PNEUMONIA" in data["probabilities"]
        assert isinstance(data["model_version"], str)
        assert isinstance(data["architecture"], str)
        assert isinstance(data["device"], str)
        assert isinstance(data["inference_time_ms"], float)
        assert isinstance(data["target_class"], str)
        assert "image_reference" in data
        assert "heatmap_reference" in data
        assert "overlay_reference" in data
        assert "original_base64" in data
        assert "heatmap_base64" in data
        assert "overlay_base64" in data
        assert "class_mapping" in data
        assert "disclaimer" in data


# 3. History Contract
def test_history_contract(mock_predictor, dummy_png_bytes):
    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        res = client.get("/history?limit=10&offset=0")
        assert res.status_code == 200
        data = res.json()

        # TypeScript AnalysisHistoryResponse contract
        assert "items" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["offset"], int)

        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "analysis_id" in item
            assert "created_at" in item
            assert "prediction" in item
            assert "confidence" in item
            assert "model_version" in item


# 4. Detail Contract
def test_detail_contract(mock_predictor, dummy_png_bytes):
    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        # First create an analysis
        files = {"file": ("chest.png", dummy_png_bytes, "image/png")}
        create_res = client.post("/analyze", files=files)
        analysis_id = create_res.json()["analysis_id"]

        # Fetch detail
        res = client.get(f"/history/{analysis_id}")
        assert res.status_code == 200
        data = res.json()

        # TypeScript AnalysisDetailResponse contract
        assert data["analysis_id"] == analysis_id
        assert "created_at" in data
        assert data["prediction"] in ["NORMAL", "PNEUMONIA"]
        assert isinstance(data["confidence"], float)
        assert isinstance(data["probabilities"], dict)
        assert "model_version" in data
        assert "architecture" in data


# 5. Error Contract
def test_error_contract():
    with TestClient(app) as client:
        # Invalid endpoint or invalid file
        files = {"file": ("invalid.txt", b"plain text", "text/plain")}
        res = client.post("/analyze", files=files)
        assert res.status_code == 400
        data = res.json()

        # TypeScript ErrorResponse contract
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert isinstance(data["error"]["code"], str)
        assert isinstance(data["error"]["message"], str)


# 6. CORS Development Compatibility
def test_cors_nextjs_compatibility():
    with TestClient(app) as client:
        res = client.options(
            "/analyze",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
