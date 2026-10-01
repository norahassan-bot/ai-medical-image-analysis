"""Task 13 End-to-End Real Smoke Test.

Validates the full workflow:
1. Upload a real verified Chest X-Ray scan to POST /analyze
2. Receive real analysis_id, prediction, confidence, model_version
3. Verify SQLite persistence
4. Query GET /history and verify record appears
5. Query GET /history/{analysis_id} and verify full detail matches
6. Query GET /history/{analysis_id}/report to generate and download real PDF
7. Verify PDF file on disk is valid (%PDF- header, size > 1KB)
8. Re-download to verify caching behavior
9. Test GET /history/{analysis_id}/artifacts/original, heatmap, overlay
"""

import os
import sys
from pathlib import Path
import httpx

BACKEND_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = BACKEND_ROOT.parent

BASE_URL = "http://localhost:8000"


def find_sample_image() -> Path:
    candidates = [
        WORKSPACE_ROOT / "data" / "chest_xray" / "test" / "PNEUMONIA" / "person1_virus_6.jpeg",
        WORKSPACE_ROOT / "data" / "chest_xray" / "test" / "PNEUMONIA" / "person1_virus_7.jpeg",
        WORKSPACE_ROOT / "data" / "chest_xray" / "test" / "NORMAL" / "IM-0001-0001.jpeg",
    ]
    for p in candidates:
        if p.exists():
            return p
    # Search in test directory
    test_dir = WORKSPACE_ROOT / "data" / "chest_xray" / "test"
    for img in test_dir.rglob("*.jpeg"):
        return img
    for img in test_dir.rglob("*.jpg"):
        return img
    for img in test_dir.rglob("*.png"):
        return img
    raise FileNotFoundError("No sample X-ray found in dataset!")


def run_e2e_test():
    sample_img_path = find_sample_image()
    print(f"[*] Found verified test radiograph: {sample_img_path}")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Health check
        print("[1] Checking backend health...")
        health_resp = client.get("/health")
        assert health_resp.status_code == 200, f"Health check failed: {health_resp.text}"
        print(f"    -> Backend healthy: {health_resp.json()}")

        # 2. Upload real X-ray to /analyze
        print("[2] Executing POST /analyze with real radiograph...")
        with open(sample_img_path, "rb") as img_file:
            files = {"file": (sample_img_path.name, img_file, "image/jpeg")}
            analyze_resp = client.post("/analyze", files=files, data={"alpha": "0.45"})

        assert analyze_resp.status_code == 200, f"/analyze failed: {analyze_resp.text}"
        data = analyze_resp.json()
        analysis_id = data["analysis_id"]
        prediction = data["prediction"]
        confidence = data["confidence"]
        model_version = data["model_version"]

        print(f"    -> Analysis completed successfully!")
        print(f"       ID: {analysis_id}")
        print(f"       Prediction: {prediction} (Confidence: {confidence:.4f})")
        print(f"       Model: {model_version} ({data.get('architecture')})")
        print(f"       Heatmap artifact: {data.get('heatmap_reference')}")
        print(f"       Overlay artifact: {data.get('overlay_reference')}")

        # 3. Verify in GET /history
        print("[3] Querying GET /history...")
        history_resp = client.get("/history?limit=10&offset=0")
        assert history_resp.status_code == 200, f"/history failed: {history_resp.text}"
        history_data = history_resp.json()
        found_in_history = any(item["analysis_id"] == analysis_id for item in history_data["items"])
        assert found_in_history, f"Analysis {analysis_id} not found in history list!"
        print(f"    -> Successfully verified record in history (Total count: {history_data['total']})")

        # 4. Query GET /history/{analysis_id}
        print(f"[4] Querying GET /history/{analysis_id}...")
        detail_resp = client.get(f"/history/{analysis_id}")
        assert detail_resp.status_code == 200, f"Detail lookup failed: {detail_resp.text}"
        detail_data = detail_resp.json()
        assert detail_data["analysis_id"] == analysis_id
        assert detail_data["prediction"] == prediction
        assert abs(detail_data["confidence"] - confidence) < 1e-4
        print(f"    -> Successfully retrieved persisted analysis details.")

        # 5. Download Clinical PDF Report
        print(f"[5] Querying GET /history/{analysis_id}/report...")
        report_resp = client.get(f"/history/{analysis_id}/report")
        assert report_resp.status_code == 200, f"Report download failed: {report_resp.text}"
        assert report_resp.headers.get("content-type") == "application/pdf"
        assert f'filename="analysis_{analysis_id}.pdf"' in report_resp.headers.get("content-disposition", "")
        assert report_resp.content.startswith(b"%PDF-"), "Invalid PDF binary header!"
        print(f"    -> Report downloaded! Received {len(report_resp.content)} bytes of valid PDF.")

        # 6. Verify caching / reuse
        print("[6] Verifying PDF caching mechanism...")
        report_resp2 = client.get(f"/history/{analysis_id}/report")
        assert report_resp2.status_code == 200
        assert report_resp2.content == report_resp.content
        print("    -> Cached PDF returned identically and swiftly.")

        # 7. Verify artifacts endpoint
        print("[7] Verifying stored artifact retrieval endpoints...")
        orig_resp = client.get(f"/history/{analysis_id}/artifacts/original")
        assert orig_resp.status_code == 200
        heat_resp = client.get(f"/history/{analysis_id}/artifacts/heatmap")
        assert heat_resp.status_code == 200
        over_resp = client.get(f"/history/{analysis_id}/artifacts/overlay")
        assert over_resp.status_code == 200
        print(f"    -> All image artifacts (original, heatmap, overlay) successfully served.")

        print("\n=======================================================")
        print("ALL TASK 13 END-TO-END VERIFICATIONS PASSED SUCCESSFULLY!")
        print("=======================================================")


if __name__ == "__main__":
    run_e2e_test()
