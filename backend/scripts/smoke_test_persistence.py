"""Real Integration and Persistence Smoke Test for Task 10.

Tests:
1. Real POST /analyze with actual checkpoint and real X-ray scan.
2. Real SQLite row persistence in backend/data/medical_ai.db.
3. Real GET /history query.
4. Real GET /history/{analysis_id} detail retrieval.
5. Application restart persistence test: verify records remain across app restarts.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from api.main import app
from database.database import get_default_db_path, get_analysis_by_id, count_analyses


def run_persistence_smoke_test():
    print("=== 1. Starting Real Integration Test ===")

    # Pick real X-ray scans
    dataset_test = Path("data/chest_xray/test")
    pneu_imgs = list((dataset_test / "PNEUMONIA").glob("*.jpeg"))
    assert len(pneu_imgs) > 0, "No pneumonia test images found"
    sample_scan = pneu_imgs[0]

    with open(sample_scan, "rb") as f:
        scan_bytes = f.read()

    db_path = get_default_db_path()
    initial_count = count_analyses(db_path)
    print(f"Initial SQLite Analysis Count: {initial_count}")

    # Phase 1: Execute POST /analyze
    analysis_id = None
    with TestClient(app) as client:
        print(f"\n--- Sending POST /analyze on {sample_scan.name} ---")
        files = {"file": (sample_scan.name, scan_bytes, "image/jpeg")}
        resp_analyze = client.post("/analyze", files=files)
        print(f"Status: {resp_analyze.status_code}")
        assert resp_analyze.status_code == 200

        data_analyze = resp_analyze.json()
        analysis_id = data_analyze["analysis_id"]
        prediction = data_analyze["prediction"]
        confidence = data_analyze["confidence"]
        created_at = data_analyze["created_at"]
        img_ref = data_analyze["image_reference"]
        heat_ref = data_analyze["heatmap_reference"]
        over_ref = data_analyze["overlay_reference"]

        print(f"Analysis ID: {analysis_id}")
        print(f"Created At: {created_at}")
        print(f"Prediction: {prediction}")
        print(f"Confidence: {confidence:.4f}")
        print(f"Image Reference: {img_ref}")
        print(f"Heatmap Reference: {heat_ref}")
        print(f"Overlay Reference: {over_ref}")

        assert analysis_id is not None
        assert prediction in ["NORMAL", "PNEUMONIA"]
        assert 0.0 <= confidence <= 1.0

        # Phase 2: Verify GET /history
        print("\n--- Querying GET /history ---")
        resp_history = client.get("/history?limit=10&offset=0")
        print(f"Status: {resp_history.status_code}")
        assert resp_history.status_code == 200
        history_data = resp_history.json()
        print(f"Total analyses in DB: {history_data['total']}")
        assert history_data["total"] >= initial_count + 1
        assert any(item["analysis_id"] == analysis_id for item in history_data["items"])

        # Phase 3: Verify GET /history/{analysis_id}
        print(f"\n--- Querying GET /history/{analysis_id} ---")
        resp_detail = client.get(f"/history/{analysis_id}")
        print(f"Status: {resp_detail.status_code}")
        assert resp_detail.status_code == 200
        detail_data = resp_detail.json()
        print(f"Detail Prediction: {detail_data['prediction']}")
        print(f"Detail Confidence: {detail_data['confidence']}")
        print(f"Detail Model Version: {detail_data['model_version']}")
        assert detail_data["analysis_id"] == analysis_id
        assert detail_data["prediction"] == prediction
        assert abs(detail_data["confidence"] - confidence) < 1e-4

    # Phase 4: Direct SQLite Verification
    print("\n=== 2. Direct SQLite Verification ===")
    direct_record = get_analysis_by_id(analysis_id, db_path)
    assert direct_record is not None
    assert direct_record["analysis_id"] == analysis_id
    assert direct_record["prediction"] == prediction
    print(f"Direct DB Record verified: {direct_record['analysis_id']} ({direct_record['prediction']})")

    # Phase 5: Application Restart Persistence Test
    print("\n=== 3. Application Restart Persistence Test ===")
    # Simulate a full application restart with fresh TestClient instance
    with TestClient(app) as client_restarted:
        resp_restart_detail = client_restarted.get(f"/history/{analysis_id}")
        assert resp_restart_detail.status_code == 200
        restarted_data = resp_restart_detail.json()
        assert restarted_data["analysis_id"] == analysis_id
        assert restarted_data["prediction"] == prediction
        print("Record successfully persisted across application restart!")

    print("\nALL REAL INTEGRATION & PERSISTENCE TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_persistence_smoke_test()
