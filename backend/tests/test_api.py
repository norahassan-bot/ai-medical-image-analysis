"""Pytest suite for FastAPI REST API Backend (Task 9).

Validates:
1. GET /health
2. /docs availability
3. /openapi.json availability
4. Valid /predict request
5. Valid /explain request
6. Valid /analyze request
7. Missing image in upload
8. Unsupported file type
9. Oversized file handling
10. Corrupted image handling
11. Invalid dimensions handling
12. Invalid request handling
13. Model unavailable handling
14. CORS configuration
15. Response schema validation
16. Internal error sanitization
"""

import io
import sys
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

from api.main import app, default_origins
from src.inference.predict import (
    ChestXRayPredictor,
    PredictionResult,
    ExplainabilityResult,
    ImageValidationError,
    ModelNotLoadedError,
)


@pytest.fixture
def mock_valid_png_bytes():
    """Create a synthetic 64x64 valid PNG byte stream."""
    img_arr = np.random.randint(50, 200, (64, 64, 3), dtype=np.uint8)
    pil_img = Image.fromarray(img_arr)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def mock_tiny_png_bytes():
    """Create a tiny 16x16 PNG byte stream (below minimum dimensions)."""
    img_arr = np.zeros((16, 16, 3), dtype=np.uint8)
    pil_img = Image.fromarray(img_arr)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def mock_predictor():
    """Create a mock predictor returning valid structured responses."""
    predictor = MagicMock(spec=ChestXRayPredictor)
    predictor.is_loaded = True
    predictor.model_version = "1.0.0-test"
    predictor.target_device = "cpu"
    mock_model = MagicMock()
    mock_model.arch_key = "resnet18"
    predictor.model = mock_model

    predictor.predict.return_value = PredictionResult(
        prediction="PNEUMONIA",
        predicted_index=1,
        confidence=0.925,
        probabilities={"NORMAL": 0.075, "PNEUMONIA": 0.925},
        model_version="1.0.0-test",
        architecture="resnet18",
        device="cpu",
        inference_time_ms=45.2,
    )

    predictor.predict_with_explanation.return_value = ExplainabilityResult(
        prediction="PNEUMONIA",
        predicted_index=1,
        confidence=0.925,
        probabilities={"NORMAL": 0.075, "PNEUMONIA": 0.925},
        model_version="1.0.0-test",
        architecture="resnet18",
        device="cpu",
        inference_time_ms=62.8,
        target_class="PNEUMONIA",
        original_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        heatmap_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        overlay_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        original_dimensions=(64, 64),
    )
    return predictor


# 1. GET /health
def test_get_health_endpoint(mock_predictor):
    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is True
        assert data["model_version"] == "1.0.0-test"
        assert data["architecture"] == "resnet18"


# 2. /docs availability
def test_docs_availability():
    with TestClient(app) as client:
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "html" in response.text.lower()


# 3. /openapi.json availability
def test_openapi_json_availability():
    with TestClient(app) as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "/predict" in data["paths"]
        assert "/explain" in data["paths"]
        assert "/analyze" in data["paths"]


# 4. Valid /predict request
def test_valid_predict_request(mock_predictor, mock_valid_png_bytes):
    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        files = {"file": ("test_xray.png", mock_valid_png_bytes, "image/png")}
        response = client.post("/predict", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["prediction"] == "PNEUMONIA"
        assert data["predicted_index"] == 1
        assert data["confidence"] == 0.925
        assert "NORMAL" in data["probabilities"]
        assert "PNEUMONIA" in data["probabilities"]
        assert data["architecture"] == "resnet18"
        assert "disclaimer" in data


# 5. Valid /explain request
def test_valid_explain_request(mock_predictor, mock_valid_png_bytes):
    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        files = {"file": ("test_xray.png", mock_valid_png_bytes, "image/png")}
        data_payload = {"target_class": 1, "alpha": 0.5}
        response = client.post("/explain", files=files, data=data_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["prediction"] == "PNEUMONIA"
        assert data["target_class"] == "PNEUMONIA"
        assert data["heatmap_base64"].startswith("data:image/png;base64,")
        assert data["overlay_base64"].startswith("data:image/png;base64,")
        assert data["original_dimensions"] == [64, 64]


# 6. Valid /analyze request
def test_valid_analyze_request(mock_predictor, mock_valid_png_bytes):
    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        files = {"file": ("chest.jpg", mock_valid_png_bytes, "image/jpeg")}
        response = client.post("/analyze", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["prediction"] == "PNEUMONIA"
        assert data["confidence"] == 0.925
        assert "probabilities" in data
        assert data["overlay_base64"] is not None


# 7. Missing image
def test_missing_image():
    with TestClient(app) as client:
        response = client.post("/predict")
        # FastAPI returns 422 for missing required multipart file parameter
        assert response.status_code in [400, 422]
        data = response.json()
        assert "error" in data or "detail" in data


# 8. Unsupported file type
def test_unsupported_file_type(mock_predictor):
    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        files = {"file": ("document.pdf", b"%PDF-1.4...", "application/pdf")}
        response = client.post("/predict", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] in ["UNSUPPORTED_FORMAT", "INVALID_IMAGE"]
        assert "Unsupported file format" in data["error"]["message"] or "valid image" in data["error"]["message"]


# 9. Oversized file handling
def test_oversized_file(mock_predictor):
    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        # Exceed MAX_FILE_SIZE_BYTES
        oversized_data = b"0" * (51 * 1024 * 1024)
        files = {"file": ("huge_xray.png", oversized_data, "image/png")}
        response = client.post("/predict", files=files)
        assert response.status_code == 413
        data = response.json()
        assert data["error"]["code"] in ["FILE_TOO_LARGE", "INVALID_IMAGE"]
        assert "exceeds maximum allowed limit" in data["error"]["message"].lower() or "exceeds" in data["error"]["message"].lower()


# 10. Corrupted image handling
def test_corrupted_image(mock_predictor):
    with TestClient(app) as client:
        # Predictor raises ImageValidationError for corrupt bytes
        mock_predictor.predict.side_effect = ImageValidationError("The uploaded file could not be processed as a valid image: corrupted or unreadable image content.")
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        corrupt_bytes = b"\xFF\xD8\xFFcorrupted_invalid_data"
        files = {"file": ("corrupt.jpg", corrupt_bytes, "image/jpeg")}
        response = client.post("/predict", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_IMAGE"
        assert "corrupted" in data["error"]["message"].lower() or "valid image" in data["error"]["message"].lower()


# 11. Invalid dimensions handling
def test_invalid_dimensions(mock_predictor):
    with TestClient(app) as client:
        mock_predictor.predict.side_effect = ImageValidationError(
            "Image spatial resolution (16x16) is below minimum allowable threshold (32x32)."
        )
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        files = {"file": ("tiny.png", b"dummy_png_bytes", "image/png")}
        response = client.post("/predict", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_IMAGE"


# 12. Invalid request handling (e.g. invalid alpha parameter)
def test_invalid_request_handling(mock_predictor, mock_valid_png_bytes):
    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        files = {"file": ("test.png", mock_valid_png_bytes, "image/png")}
        # Alpha should be between 0.0 and 1.0; 2.5 is invalid
        response = client.post("/explain", files=files, data={"alpha": 2.5})
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"


# 13. Model unavailable handling
def test_model_unavailable_handling(mock_valid_png_bytes):
    with TestClient(app) as client:
        app.state.predictor = None
        app.state.model_loaded = False

        files = {"file": ("test.png", mock_valid_png_bytes, "image/png")}
        response = client.post("/predict", files=files)
        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "MODEL_NOT_AVAILABLE"


# 14. CORS configuration
def test_cors_headers():
    with TestClient(app) as client:
        response = client.options(
            "/predict",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


# 15. Response schema validation
def test_response_schema_validation(mock_predictor, mock_valid_png_bytes):
    with TestClient(app) as client:
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        files = {"file": ("chest.png", mock_valid_png_bytes, "image/png")}
        response = client.post("/analyze", files=files)
        assert response.status_code == 200
        data = response.json()

        required_keys = [
            "prediction", "predicted_index", "confidence", "probabilities",
            "model_version", "architecture", "device", "inference_time_ms",
            "target_class", "original_base64", "heatmap_base64", "overlay_base64",
            "class_mapping", "disclaimer"
        ]
        for key in required_keys:
            assert key in data, f"Missing key '{key}' in AnalysisResponse"


# 16. Internal error sanitization
def test_internal_error_sanitization(mock_predictor, mock_valid_png_bytes):
    with TestClient(app, raise_server_exceptions=False) as client:
        mock_predictor.predict.side_effect = Exception("Hidden internal stack trace at line 42")
        app.state.predictor = mock_predictor
        app.state.model_loaded = True

        files = {"file": ("xray.png", mock_valid_png_bytes, "image/png")}
        response = client.post("/predict", files=files)
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "stack trace" not in data["error"]["message"].lower()
