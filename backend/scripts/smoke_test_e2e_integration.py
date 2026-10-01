"""Full End-to-End Next.js <-> FastAPI Integration Verification.

Verifies live connectivity between:
- Next.js running on http://localhost:3000
- FastAPI running on http://localhost:8000
"""

import sys
import urllib.request
import urllib.error
import json
from pathlib import Path

def test_live_integration():
    print("=== Next.js <-> FastAPI Live Integration Verification ===")

    # 1. Test FastAPI Health
    print("\n1. Testing FastAPI Health (http://localhost:8000/health)...")
    req = urllib.request.Request("http://localhost:8000/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        health_data = json.loads(resp.read().decode())
        print(f"Health Response: {health_data}")
        assert health_data["status"] == "healthy"
        assert health_data["model_loaded"] is True

    # 2. Test Next.js Dashboard Home
    print("\n2. Testing Next.js Dashboard Home (http://localhost:3000/)...")
    req = urllib.request.Request("http://localhost:3000/")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        html = resp.read().decode()
        assert "MED-VISION AI" in html or "Clinical Decision Support" in html
        print("Next.js Dashboard rendered successfully with navigation & branding.")

    # 3. Test Next.js Analysis Page
    print("\n3. Testing Next.js Analysis Page (http://localhost:3000/analysis)...")
    req = urllib.request.Request("http://localhost:3000/analysis")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        html = resp.read().decode()
        assert "AI Chest Radiograph Analysis" in html or "Drag &amp; Drop" in html or "Select or Drag" in html
        print("Next.js Analysis page rendered successfully with upload dropzone.")

    # 4. Test Next.js History Page
    print("\n4. Testing Next.js History Page (http://localhost:3000/history)...")
    req = urllib.request.Request("http://localhost:3000/history")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        html = resp.read().decode()
        assert "Clinical Analysis History" in html or "Analysis ID" in html
        print("Next.js History page rendered successfully.")

    # 5. Test Next.js System Page
    print("\n5. Testing Next.js System Page (http://localhost:3000/system)...")
    req = urllib.request.Request("http://localhost:3000/system")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        html = resp.read().decode()
        assert "System Information" in html
        print("Next.js System Info page rendered successfully.")

    # 6. Test Real AI Inference & Persistence on FastAPI
    print("\n6. Testing Real Inference POST /analyze on Live FastAPI Backend...")
    dataset_test = Path("data/chest_xray/test")
    pneu_imgs = list((dataset_test / "PNEUMONIA").glob("*.jpeg"))
    sample_scan = pneu_imgs[0]
    scan_bytes = sample_scan.read_bytes()

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{sample_scan.name}"\r\n'.encode())
    body.extend(b"Content-Type: image/jpeg\r\n\r\n")
    body.extend(scan_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        "http://localhost:8000/analyze",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        analysis_data = json.loads(resp.read().decode())
        analysis_id = analysis_data["analysis_id"]
        print(f"Analysis ID: {analysis_id}")
        print(f"Prediction: {analysis_data['prediction']}")
        print(f"Confidence: {analysis_data['confidence']:.4f}")
        print(f"Latency: {analysis_data['inference_time_ms']} ms")
        assert analysis_data["prediction"] in ["NORMAL", "PNEUMONIA"]
        assert analysis_data["heatmap_base64"].startswith("data:image/png;base64,")

    # 7. Test History Query for new analysis
    print(f"\n7. Verifying History contains Analysis {analysis_id}...")
    req = urllib.request.Request(f"http://localhost:8000/history/{analysis_id}")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        detail = json.loads(resp.read().decode())
        assert detail["analysis_id"] == analysis_id
        assert detail["prediction"] == analysis_data["prediction"]
        print(f"Retrieved persisted record {analysis_id} from SQLite successfully!")

    print("\n=== ALL NEXT.JS <-> FASTAPI LIVE INTEGRATION CHECKS PASSED! ===")


if __name__ == "__main__":
    test_live_integration()
