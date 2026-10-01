"""Pytest suite for Reusable AI Inference Engine (Task 8).

Validates:
1. Predictor initialization.
2. Model checkpoint loading.
3. CPU device selection.
4. CUDA detection when available.
5. Valid image preprocessing.
6. Invalid file type handling.
7. Missing file handling.
8. Corrupted image handling.
9. Invalid dimensions handling.
10. Prediction result structure.
11. Class mapping.
12. Confidence calculation.
13. Model version retrieval.
14. Explainability mode.
15. Grad-CAM integration.
16. Missing checkpoint handling.
17. Invalid checkpoint handling.
18. Singleton predictor behavior.
"""

import os
import io
import sys
import shutil
import numpy as np
from PIL import Image
from pathlib import Path
import pytest
import torch

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from src.inference.predict import (
    ChestXRayPredictor,
    PredictionResult,
    ExplainabilityResult,
    validate_and_load_image,
    get_default_predictor,
    InferenceError,
    ImageValidationError,
    ModelNotLoadedError,
)
from src.data.dataset import CLASS_TO_IDX, IDX_TO_CLASS
from src.models.model import build_model, save_model_checkpoint


TEST_TEMP_DIR = backend_root / "tests" / ".test_tmp"


@pytest.fixture(scope="session")
def dummy_checkpoint():
    """Create a temporary valid model checkpoint on E: drive for fast unit testing."""
    TEST_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = TEST_TEMP_DIR / "test_model.pth"
    model = build_model(architecture="resnet18", num_classes=2, pretrained=False)
    save_model_checkpoint(
        model=model,
        filepath=ckpt_path,
        optimizer=None,
        epoch=1,
        metrics={"val_f1": 0.95, "val_acc": 0.96},
        extra_config={"model_version": "1.0.0-test", "architecture": "resnet18"},
    )
    yield ckpt_path
    if ckpt_path.exists():
        try:
            ckpt_path.unlink()
        except Exception:
            pass


@pytest.fixture
def valid_pil_image():
    """Create a valid synthetic PIL Image fixture (64x64 RGB)."""
    arr = np.random.randint(50, 200, (64, 64, 3), dtype=np.uint8)
    return Image.fromarray(arr)


@pytest.fixture
def valid_image_file(valid_pil_image):
    """Save a valid PNG image file to local test directory."""
    TEST_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    file_path = TEST_TEMP_DIR / "sample_xray.png"
    valid_pil_image.save(file_path, format="PNG")
    yield file_path
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception:
            pass


# 1. Predictor initialization
def test_predictor_initialization(dummy_checkpoint):
    predictor = ChestXRayPredictor(
        checkpoint_path=dummy_checkpoint,
        device="cpu",
        model_version="1.0.0",
        auto_load=True,
    )
    assert predictor.is_loaded is True
    assert predictor.model is not None
    assert predictor.model_version == "1.0.0"
    assert str(predictor.target_device) == "cpu"


# 2. Model checkpoint loading
def test_model_checkpoint_loading(dummy_checkpoint):
    predictor = ChestXRayPredictor(
        checkpoint_path=dummy_checkpoint,
        device="cpu",
        auto_load=False,
    )
    assert predictor.is_loaded is False
    success = predictor.load_model()
    assert success is True
    assert predictor.is_loaded is True
    assert predictor.model.arch_key == "resnet18"


# 3. CPU device selection
def test_cpu_device_selection(dummy_checkpoint):
    predictor = ChestXRayPredictor(
        checkpoint_path=dummy_checkpoint,
        device="cpu",
    )
    assert str(predictor.target_device) == "cpu"
    for param in predictor.model.parameters():
        assert param.device.type == "cpu"
        break


# 4. CUDA detection when available
def test_cuda_detection(dummy_checkpoint):
    if torch.cuda.is_available():
        predictor = ChestXRayPredictor(
            checkpoint_path=dummy_checkpoint,
            device="cuda",
        )
        assert predictor.target_device.type == "cuda"
    else:
        predictor = ChestXRayPredictor(
            checkpoint_path=dummy_checkpoint,
            device=None,
        )
        assert predictor.target_device.type == "cpu"


# 5. Valid image preprocessing
def test_valid_image_preprocessing(valid_pil_image, valid_image_file):
    # From PIL Image
    pil_res, dims = validate_and_load_image(valid_pil_image)
    assert isinstance(pil_res, Image.Image)
    assert dims == (64, 64)

    # From File Path
    file_res, dims_f = validate_and_load_image(valid_image_file)
    assert isinstance(file_res, Image.Image)
    assert dims_f == (64, 64)

    # From Raw Bytes
    with open(valid_image_file, "rb") as f:
        raw_bytes = f.read()
    bytes_res, dims_b = validate_and_load_image(raw_bytes)
    assert isinstance(bytes_res, Image.Image)
    assert dims_b == (64, 64)


# 6. Invalid file type handling
def test_invalid_file_type():
    TEST_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    invalid_file = TEST_TEMP_DIR / "document.txt"
    invalid_file.write_text("Not an image")
    try:
        with pytest.raises(ImageValidationError) as excinfo:
            validate_and_load_image(invalid_file)
        assert "Unsupported image extension" in str(excinfo.value)
    finally:
        if invalid_file.exists():
            invalid_file.unlink()


# 7. Missing file handling
def test_missing_file_handling():
    missing_path = Path("data/chest_xray/non_existent_image_12345.png")
    with pytest.raises(ImageValidationError) as excinfo:
        validate_and_load_image(missing_path)
    assert "Image file does not exist" in str(excinfo.value)


# 8. Corrupted image handling
def test_corrupted_image_handling():
    TEST_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    corrupted_file = TEST_TEMP_DIR / "corrupted.jpg"
    corrupted_file.write_bytes(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00corrupted_garbage_bytes")
    try:
        with pytest.raises(ImageValidationError) as excinfo:
            validate_and_load_image(corrupted_file)
        assert "corrupted" in str(excinfo.value).lower() or "valid image" in str(excinfo.value).lower()
    finally:
        if corrupted_file.exists():
            corrupted_file.unlink()


# 9. Invalid dimensions handling
def test_invalid_dimensions_handling():
    tiny_img = Image.fromarray(np.zeros((16, 16, 3), dtype=np.uint8))
    with pytest.raises(ImageValidationError) as excinfo:
        validate_and_load_image(tiny_img, min_dimension=32)
    assert "below minimum allowable threshold" in str(excinfo.value)


# 10. Prediction result structure
def test_prediction_result_structure(dummy_checkpoint, valid_pil_image):
    predictor = ChestXRayPredictor(checkpoint_path=dummy_checkpoint, device="cpu")
    result = predictor.predict(valid_pil_image)

    assert isinstance(result, PredictionResult)
    assert result.prediction in ["NORMAL", "PNEUMONIA"]
    assert result.predicted_index in [0, 1]
    assert isinstance(result.confidence, float)
    assert 0.0 <= result.confidence <= 1.0
    assert "NORMAL" in result.probabilities
    assert "PNEUMONIA" in result.probabilities
    assert isinstance(result.model_version, str)
    assert isinstance(result.architecture, str)
    assert result.device == "cpu"
    assert result.inference_time_ms > 0

    d = result.to_dict()
    assert isinstance(d, dict)
    assert d["prediction"] == result.prediction


# 11. Class mapping
def test_class_mapping_consistency(dummy_checkpoint, valid_pil_image):
    predictor = ChestXRayPredictor(checkpoint_path=dummy_checkpoint, device="cpu")
    result = predictor.predict(valid_pil_image)
    assert result.class_mapping == {"NORMAL": 0, "PNEUMONIA": 1}
    assert IDX_TO_CLASS[result.predicted_index] == result.prediction


# 12. Confidence calculation
def test_confidence_calculation(dummy_checkpoint, valid_pil_image):
    predictor = ChestXRayPredictor(checkpoint_path=dummy_checkpoint, device="cpu")
    result = predictor.predict(valid_pil_image)
    probs = result.probabilities
    # Probabilities must sum to ~1.0
    assert abs((probs["NORMAL"] + probs["PNEUMONIA"]) - 1.0) < 0.01
    assert result.confidence == max(probs["NORMAL"], probs["PNEUMONIA"])


# 13. Model version retrieval
def test_model_version_retrieval(dummy_checkpoint, valid_pil_image):
    predictor = ChestXRayPredictor(
        checkpoint_path=dummy_checkpoint,
        device="cpu",
        model_version="2.1.4",
    )
    result = predictor.predict(valid_pil_image)
    assert result.model_version == "2.1.4"


# 14. Explainability mode
def test_explainability_mode(dummy_checkpoint, valid_pil_image):
    predictor = ChestXRayPredictor(checkpoint_path=dummy_checkpoint, device="cpu")
    result = predictor.predict_with_explanation(valid_pil_image, encode_base64=True)

    assert isinstance(result, ExplainabilityResult)
    assert result.prediction in ["NORMAL", "PNEUMONIA"]
    assert result.target_class in ["NORMAL", "PNEUMONIA"]
    assert result.confidence >= 0.0
    assert result.original_base64 is not None
    assert result.original_base64.startswith("data:image/png;base64,")
    assert result.heatmap_base64 is not None
    assert result.heatmap_base64.startswith("data:image/png;base64,")
    assert result.overlay_base64 is not None
    assert result.overlay_base64.startswith("data:image/png;base64,")
    assert result.original_dimensions == (64, 64)
    assert "Grad-CAM" in result.disclaimer


# 15. Grad-CAM integration
def test_gradcam_integration_custom_target(dummy_checkpoint, valid_pil_image):
    predictor = ChestXRayPredictor(checkpoint_path=dummy_checkpoint, device="cpu")
    result = predictor.predict_with_explanation(valid_pil_image, target_class=1)
    assert result.target_class == "PNEUMONIA"


# 16. Missing checkpoint handling
def test_missing_checkpoint_handling():
    with pytest.raises((FileNotFoundError, InferenceError)):
        ChestXRayPredictor(
            checkpoint_path="non_existent/path/to/missing_model.pth",
            auto_load=True,
        )


# 17. Invalid checkpoint handling
def test_invalid_checkpoint_handling():
    TEST_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    invalid_ckpt = TEST_TEMP_DIR / "corrupted_model.pth"
    invalid_ckpt.write_bytes(b"NOT_A_VALID_PYTORCH_STATE_DICT")
    try:
        with pytest.raises(InferenceError):
            ChestXRayPredictor(
                checkpoint_path=invalid_ckpt,
                auto_load=True,
            )
    finally:
        if invalid_ckpt.exists():
            invalid_ckpt.unlink()


# 18. Singleton predictor test
def test_singleton_predictor(dummy_checkpoint):
    p1 = get_default_predictor(checkpoint_path=str(dummy_checkpoint), device="cpu")
    p2 = get_default_predictor(checkpoint_path=str(dummy_checkpoint), device="cpu")
    assert p1 is p2
