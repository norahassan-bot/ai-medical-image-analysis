"""End-to-End Task 16 Verification Script.

Comprehensive verification of:
- Environment & dependencies
- Dataset integrity & isolation
- Preprocessing & DataLoaders
- Model architecture & weights loading
- Grad-CAM heatmap generation
- Inference Engine
- FastAPI endpoints
- SQLite persistence
- Clinical PDF report generation
- Security & error handling
"""

import os
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

print("=" * 70)
print("TASK 16 — FINAL END-TO-END VERIFICATION RUNNER")
print("=" * 70)

# 1. Environment & Imports
print("\n[1/10] Verifying Python Environment & Imports...")
import torch
import torchvision
import sklearn
import cv2
import PIL
import fastapi
import uvicorn
import pydantic
import sqlalchemy
import reportlab
import pytest
import httpx

print(f"  - Python Version: {sys.version.split()[0]}")
print(f"  - PyTorch: {torch.__version__} (CUDA Available: {torch.cuda.is_available()})")
print(f"  - Torchvision: {torchvision.__version__}")
print(f"  - Scikit-Learn: {sklearn.__version__}")
print(f"  - OpenCV: {cv2.__version__}")
print(f"  - Pillow: {PIL.__version__}")
print(f"  - FastAPI: {fastapi.__version__}")
print(f"  - Pydantic: {pydantic.__version__}")
print(f"  - ReportLab: {reportlab.__version__}")

# 2. Dataset Verification
print("\n[2/10] Verifying Dataset Structure & Sample Counts...")
data_dir = backend_root.parent / "data" / "chest_xray"
train_norm = len(list((data_dir / "train" / "NORMAL").glob("*.*")))
train_pneu = len(list((data_dir / "train" / "PNEUMONIA").glob("*.*")))
val_norm = len(list((data_dir / "val" / "NORMAL").glob("*.*")))
val_pneu = len(list((data_dir / "val" / "PNEUMONIA").glob("*.*")))
test_norm = len(list((data_dir / "test" / "NORMAL").glob("*.*")))
test_pneu = len(list((data_dir / "test" / "PNEUMONIA").glob("*.*")))

print(f"  - Train Split: {train_norm} NORMAL, {train_pneu} PNEUMONIA (Total: {train_norm + train_pneu})")
print(f"  - Val Split:   {val_norm} NORMAL, {val_pneu} PNEUMONIA (Total: {val_norm + val_pneu})")
print(f"  - Test Split:  {test_norm} NORMAL, {test_pneu} PNEUMONIA (Total: {test_norm + test_pneu})")
print(f"  - Grand Total: {train_norm + train_pneu + val_norm + val_pneu + test_norm + test_pneu} images")

assert (train_norm + train_pneu + val_norm + val_pneu + test_norm + test_pneu) == 5856, "Dataset sample count mismatch!"

# 3. Preprocessing & DataLoaders
print("\n[3/10] Verifying DataLoaders & Preprocessing...")
from src.data.dataset import create_dataloaders
dataloaders = create_dataloaders(dataset_root=data_dir, batch_size=16, num_workers=0)
train_loader = dataloaders["train"]
val_loader = dataloaders["val"]
test_loader = dataloaders["test"]
images, labels = next(iter(train_loader))
print(f"  - Train batch shape: {images.shape}, labels shape: {labels.shape}")
print(f"  - Image tensor dtype: {images.dtype}, min: {images.min():.2f}, max: {images.max():.2f}")

# 4. Model Architecture & Checkpoint
print("\n[4/10] Verifying Model Architecture & Real Checkpoint...")
from src.models.model import build_model, MedicalClassifier
ckpt_path = backend_root / "models" / "best_model.pth"
assert ckpt_path.exists(), f"Checkpoint {ckpt_path} missing!"
model = build_model("resnet18", num_classes=2, pretrained=False)
checkpoint = torch.load(ckpt_path, map_location="cpu")
state_dict = checkpoint.get("state_dict") or checkpoint.get("model_state_dict") or checkpoint
model.load_state_dict(state_dict)
model.eval()
total_params = sum(p.numel() for p in model.parameters())
print(f"  - Model architecture: ResNet18 ({total_params:,} parameters)")
print(f"  - Loaded checkpoint: {ckpt_path} ({ckpt_path.stat().st_size / (1024*1024):.2f} MB)")

# 5. Grad-CAM Explainability
print("\n[5/10] Verifying Grad-CAM Heatmap Generation with Real X-ray...")
from src.explainability.gradcam import explain_medical_image
sample_xray = next((data_dir / "test" / "PNEUMONIA").glob("*.jpeg"))
print(f"  - Using real test radiograph: {sample_xray.name}")
cam_res = explain_medical_image(model=model, image_input=sample_xray, target_class=1)
print(f"  - Grad-CAM heatmap shape: {cam_res['heatmap_rgb'].shape}")
print(f"  - Overlay shape: {cam_res['overlay_rgb'].shape}")
print(f"  - Predicted class name: {cam_res['predicted_class_name']} (Confidence: {cam_res['confidence']:.4f})")

# 6. Inference Engine
print("\n[6/10] Verifying Inference Engine Pipeline...")
from src.inference.predict import ChestXRayPredictor
predictor = ChestXRayPredictor(checkpoint_path=ckpt_path, auto_load=True)
infer_res = predictor.predict_with_explanation(sample_xray.read_bytes(), encode_base64=True)
print(f"  - Diagnostic Prediction: {infer_res.prediction} (Confidence: {infer_res.confidence:.4f})")
print(f"  - Probabilities: {infer_res.probabilities}")
print(f"  - Inference latency: {infer_res.inference_time_ms:.2f} ms")
print(f"  - Heatmap base64 length: {len(infer_res.heatmap_base64)} chars")

# 7. FastAPI Endpoints & Integration
print("\n[7/10] Verifying FastAPI Endpoints & Real /analyze Request...")
from fastapi.testclient import TestClient
from api.main import app

with TestClient(app) as client:
    # Health endpoint
    health_res = client.get("/health")
    assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
    print(f"  - GET /health: 200 OK -> {health_res.json()}")

    # OpenAPI Docs
    docs_res = client.get("/docs")
    assert docs_res.status_code == 200, "Docs check failed!"
    print("  - GET /docs: 200 OK")

    # Real /analyze multipart upload
    with open(sample_xray, "rb") as f:
        analyze_res = client.post("/analyze", files={"file": (sample_xray.name, f, "image/jpeg")})

    assert analyze_res.status_code == 200, f"/analyze failed: {analyze_res.text}"
    analyze_data = analyze_res.json()
    analysis_id = analyze_data["analysis_id"]
    print(f"  - POST /analyze: 200 OK -> Created Analysis ID: {analysis_id}")
    print(f"    Prediction: {analyze_data['prediction']} | Confidence: {analyze_data['confidence']}")

    # 8. SQLite Persistence Verification
    print("\n[8/10] Verifying SQLite Database History & Persistence...")
    history_res = client.get("/history?limit=10")
    assert history_res.status_code == 200
    history_data = history_res.json()
    print(f"  - GET /history: 200 OK -> Total records in DB: {history_data['total']}")

    detail_res = client.get(f"/history/{analysis_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["analysis_id"] == analysis_id
    print(f"  - GET /history/{analysis_id}: 200 OK -> Retrieved record successfully")

    # 9. Clinical PDF Report Generation
    print("\n[9/10] Verifying Clinical PDF Report Generation...")
    report_res = client.get(f"/history/{analysis_id}/report")
    assert report_res.status_code == 200
    assert "application/pdf" in report_res.headers.get("content-type", "")
    pdf_bytes = report_res.content
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")
    print(f"  - GET /history/{analysis_id}/report: 200 OK -> PDF size: {len(pdf_bytes):,} bytes (Valid %PDF header)")

    # 10. Security & Error Handling Verification
    print("\n[10/10] Verifying Security Sanitization & Validation...")
    # Path traversal analysis ID
    bad_id_res = client.get("/history/../../../etc/passwd")
    assert bad_id_res.status_code in [400, 404]
    print(f"  - Path traversal analysis_id rejected with HTTP {bad_id_res.status_code}")

    # Invalid file upload
    bad_file_res = client.post("/analyze", files={"file": ("malicious.exe", b"MZ\x90\x00", "application/x-msdownload")})
    assert bad_file_res.status_code == 400
    print(f"  - Unsupported file format rejected with HTTP {bad_file_res.status_code}")

    # Oversized payload (limit is 15MB)
    oversized_res = client.post("/analyze", files={"file": ("huge.jpg", b"0" * (16 * 1024 * 1024), "image/jpeg")})
    assert oversized_res.status_code == 413
    print(f"  - Oversized file rejected with HTTP {oversized_res.status_code}")

print("\n" + "=" * 70)
print("ALL 10 VERIFICATION MODULES PASSED SUCCESSFULLY (100%)")
print("=" * 70)
