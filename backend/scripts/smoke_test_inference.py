"""Real Smoke Test for Task 8 Reusable AI Inference Engine.

Performs real end-to-end inference using:
- The actual trained checkpoint from Task 5 (backend/models/best_model.pth)
- Real chest radiograph scans from data/chest_xray/test/
"""

import sys
from pathlib import Path
from PIL import Image

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from src.inference.predict import ChestXRayPredictor


def run_smoke_test():
    checkpoint_path = backend_root / "models" / "best_model.pth"
    assert checkpoint_path.exists(), f"Checkpoint missing: {checkpoint_path}"

    # Pick real X-ray images
    dataset_test = Path("data/chest_xray/test")
    pneumonia_samples = list((dataset_test / "PNEUMONIA").glob("*.jpeg"))
    normal_samples = list((dataset_test / "NORMAL").glob("*.jpeg"))

    assert len(pneumonia_samples) > 0, "No pneumonia sample images found in test set"
    assert len(normal_samples) > 0, "No normal sample images found in test set"

    sample_pneu = pneumonia_samples[0]
    sample_norm = normal_samples[0]

    print(f"=== Initializing Predictor ===")
    predictor = ChestXRayPredictor(
        checkpoint_path=checkpoint_path,
        model_version="1.0.0",
    )
    print(f"Loaded: {predictor.is_loaded}")
    print(f"Device: {predictor.target_device}")
    print(f"Architecture: {predictor.model.arch_key}")

    print(f"\n=== Test 1: Standard Prediction on Pneumonia Scan ({sample_pneu.name}) ===")
    res_pneu = predictor.predict(sample_pneu)
    print(f"Prediction: {res_pneu.prediction}")
    print(f"Confidence: {res_pneu.confidence:.4f}")
    print(f"Probabilities: {res_pneu.probabilities}")
    print(f"Model Version: {res_pneu.model_version}")
    print(f"Latency: {res_pneu.inference_time_ms} ms")
    assert res_pneu.prediction in ["NORMAL", "PNEUMONIA"]
    assert 0.0 <= res_pneu.confidence <= 1.0

    print(f"\n=== Test 2: Standard Prediction on Normal Scan ({sample_norm.name}) ===")
    res_norm = predictor.predict(sample_norm)
    print(f"Prediction: {res_norm.prediction}")
    print(f"Confidence: {res_norm.confidence:.4f}")
    print(f"Probabilities: {res_norm.probabilities}")
    print(f"Latency: {res_norm.inference_time_ms} ms")
    assert res_norm.prediction in ["NORMAL", "PNEUMONIA"]

    print(f"\n=== Test 3: Explainability Mode on Pneumonia Scan ===")
    expl_pneu = predictor.predict_with_explanation(sample_pneu, encode_base64=True)
    print(f"Prediction: {expl_pneu.prediction}")
    print(f"Confidence: {expl_pneu.confidence:.4f}")
    print(f"Target Class: {expl_pneu.target_class}")
    print(f"Original b64 present: {expl_pneu.original_base64 is not None} (Length: {len(expl_pneu.original_base64) if expl_pneu.original_base64 else 0})")
    print(f"Heatmap b64 present: {expl_pneu.heatmap_base64 is not None} (Length: {len(expl_pneu.heatmap_base64) if expl_pneu.heatmap_base64 else 0})")
    print(f"Overlay b64 present: {expl_pneu.overlay_base64 is not None} (Length: {len(expl_pneu.overlay_base64) if expl_pneu.overlay_base64 else 0})")
    print(f"Original Dimensions: {expl_pneu.original_dimensions}")

    assert expl_pneu.heatmap_base64.startswith("data:image/png;base64,")
    assert expl_pneu.overlay_base64.startswith("data:image/png;base64,")

    print("\nALL REAL SMOKE TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_smoke_test()
