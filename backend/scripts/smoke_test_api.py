"""Real Endpoint Smoke Test for FastAPI REST API (Task 9).

Executes real HTTP requests against FastAPI app using:
- The actual trained checkpoint (backend/models/best_model.pth)
- Real chest radiograph scans from data/chest_xray/test/
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from api.main import app


def run_api_smoke_test():
    print("=== Starting Real API Smoke Test ===")

    # Pick real X-ray scans
    dataset_test = Path("data/chest_xray/test")
    pneu_imgs = list((dataset_test / "PNEUMONIA").glob("*.jpeg"))
    norm_imgs = list((dataset_test / "NORMAL").glob("*.jpeg"))

    assert len(pneu_imgs) > 0, "No pneumonia test images found"
    assert len(norm_imgs) > 0, "No normal test images found"

    sample_pneu_path = pneu_imgs[0]
    sample_norm_path = norm_imgs[0]

    with open(sample_pneu_path, "rb") as f:
        pneu_bytes = f.read()

    with open(sample_norm_path, "rb") as f:
        norm_bytes = f.read()

    with TestClient(app) as client:
        # 1. Test GET /health
        print("\n--- 1. Testing GET /health ---")
        res_health = client.get("/health")
        print(f"Status: {res_health.status_code}")
        print(f"Response: {res_health.json()}")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"
        assert res_health.json()["model_loaded"] is True

        # 2. Test GET /docs
        print("\n--- 2. Testing GET /docs ---")
        res_docs = client.get("/docs")
        print(f"Status: {res_docs.status_code}")
        assert res_docs.status_code == 200

        # 3. Test GET /openapi.json
        print("\n--- 3. Testing GET /openapi.json ---")
        res_openapi = client.get("/openapi.json")
        print(f"Status: {res_openapi.status_code}")
        assert res_openapi.status_code == 200
        schema = res_openapi.json()
        assert "/predict" in schema["paths"]
        assert "/explain" in schema["paths"]
        assert "/analyze" in schema["paths"]

        # 4. Test POST /predict on real pneumonia scan
        print(f"\n--- 4. Testing POST /predict on {sample_pneu_path.name} ---")
        files = {"file": (sample_pneu_path.name, pneu_bytes, "image/jpeg")}
        res_pred = client.post("/predict", files=files)
        print(f"Status: {res_pred.status_code}")
        pred_data = res_pred.json()
        print(f"Prediction: {pred_data['prediction']}")
        print(f"Confidence: {pred_data['confidence']}")
        print(f"Probabilities: {pred_data['probabilities']}")
        print(f"Latency: {pred_data['inference_time_ms']} ms")
        assert res_pred.status_code == 200
        assert pred_data["prediction"] in ["NORMAL", "PNEUMONIA"]

        # 5. Test POST /explain on real pneumonia scan
        print(f"\n--- 5. Testing POST /explain on {sample_pneu_path.name} ---")
        files = {"file": (sample_pneu_path.name, pneu_bytes, "image/jpeg")}
        res_expl = client.post("/explain", files=files, data={"alpha": 0.45})
        print(f"Status: {res_expl.status_code}")
        expl_data = res_expl.json()
        print(f"Prediction: {expl_data['prediction']}")
        print(f"Confidence: {expl_data['confidence']}")
        print(f"Target Class: {expl_data['target_class']}")
        print(f"Heatmap present: {expl_data['heatmap_base64'] is not None}")
        print(f"Overlay present: {expl_data['overlay_base64'] is not None}")
        print(f"Original Dims: {expl_data['original_dimensions']}")
        assert res_expl.status_code == 200
        assert expl_data["heatmap_base64"].startswith("data:image/png;base64,")
        assert expl_data["overlay_base64"].startswith("data:image/png;base64,")

        # 6. Test POST /analyze on real normal scan
        print(f"\n--- 6. Testing POST /analyze on {sample_norm_path.name} ---")
        files = {"file": (sample_norm_path.name, norm_bytes, "image/jpeg")}
        res_anal = client.post("/analyze", files=files)
        print(f"Status: {res_anal.status_code}")
        anal_data = res_anal.json()
        print(f"Prediction: {anal_data['prediction']}")
        print(f"Confidence: {anal_data['confidence']}")
        print(f"Probabilities: {anal_data['probabilities']}")
        print(f"Overlay present: {anal_data['overlay_base64'] is not None}")
        assert res_anal.status_code == 200
        assert anal_data["prediction"] in ["NORMAL", "PNEUMONIA"]

    print("\n=== ALL REAL API SMOKE TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    run_api_smoke_test()
