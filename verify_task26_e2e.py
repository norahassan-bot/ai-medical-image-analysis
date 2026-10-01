"""
End-to-End Verification Script for Task 26:
Prescription Reader Backend API, Database Persistence & Flow
"""
import os
import sys
import io
import json
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from api.main import app

def create_synthetic_prescription_image():
    import numpy as np
    import cv2
    canvas = np.full((800, 600, 3), 255, dtype=np.uint8)
    cv2.putText(canvas, "Dr. Smith Clinic", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(canvas, "Rx:", (50, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    cv2.putText(canvas, "Augmentin 1g", (60, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(canvas, "1 tab every 12h for 5 days after food", (60, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(canvas, "Panadol 500mg", (60, 370), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(canvas, "1-2 tablets prn for pain", (60, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    _, buffer = cv2.imencode(".jpg", canvas)
    return buffer.tobytes()

def run_e2e_verification():
    print("=== Starting Task 26 E2E Verification ===")
    client = TestClient(app)
    
    # 1. Test POST /prescription/analyze
    print("\n[Step 1] Uploading and analyzing real prescription image...")
    image_bytes = create_synthetic_prescription_image()
    files = {"file": ("prescription_sample.jpg", image_bytes, "image/jpeg")}
    
    response = client.post("/prescription/analyze", files=files)
    assert response.status_code == 200, f"Analysis failed with status {response.status_code}: {response.text}"
    
    data = response.json()
    print(f"-> Full response keys: {list(data.keys())}")
    print(f"-> Total medications: {data.get('total_medications')}")
    print(f"-> Result inner keys: {list(data.get('result', {}).keys())}")
    print(f"-> Result medications count: {len(data.get('result', {}).get('medications', []))}")
    
    analysis_id = data.get("analysis_id")
    assert analysis_id is not None, "Missing analysis_id"
    
    # Check inner result medications
    meds = data.get("result", {}).get("medications", [])
    print(f"-> Parsed medications in result: {len(meds)}")
    
    if len(meds) > 0:
        first_med = meds[0]
        med_summary = first_med.get("medication", {})
        print(f"-> First medication candidate: {med_summary.get('matched_name')} (Confidence: {med_summary.get('confidence')})")
        print(f"-> Educational Info available: {first_med.get('medication_information') is not None}")
        if first_med.get("instructions"):
            inst = first_med["instructions"]
            print(f"-> Parsed Instructions: Dose={inst.get('dose', {}).get('raw_value') if inst.get('dose') else None}, Freq={inst.get('frequency', {}).get('raw_value') if inst.get('frequency') else None}")
    
    # 2. Test GET /prescription/history
    print("\n[Step 2] Retrieving user prescription history...")
    history_resp = client.get("/prescription/history")
    assert history_resp.status_code == 200, f"History fetch failed: {history_resp.text}"
    history_data = history_resp.json()
    items = history_data.get("items", [])
    print(f"-> User prescription history items count: {len(items)}")
    matching_item = next((i for i in items if i.get("id") == analysis_id), None)
    assert matching_item is not None, "Created analysis not found in user history"
    print("-> Successfully verified analysis in user history!")

    # 3. Test GET /prescription/history/{id}
    print(f"\n[Step 3] Retrieving prescription detail for ID: {analysis_id}...")
    detail_resp = client.get(f"/prescription/history/{analysis_id}")
    assert detail_resp.status_code == 200, f"Detail fetch failed: {detail_resp.text}"
    detail_data = detail_resp.json()
    assert detail_data.get("id") == analysis_id, "Detail id mismatch"
    detail_meds = detail_data.get("result", {}).get("medications", [])
    assert len(detail_meds) == len(meds), "Medications count mismatch"
    print("-> Successfully verified prescription detail retrieved with complete structured result!")

    # 4. Test GET /prescription/history/{id}/artifacts/original_image
    print("\n[Step 4] Retrieving original prescription image artifact...")
    art_resp = client.get(f"/prescription/history/{analysis_id}/artifacts/original_image")
    assert art_resp.status_code == 200, f"Artifact fetch failed: {art_resp.text}"
    assert len(art_resp.content) > 0, "Empty artifact content"
    print(f"-> Retrieved original image artifact ({len(art_resp.content)} bytes)")

    # 5. Test Admin Prescriptions Endpoint
    print("\n[Step 5] Testing admin authorization on /admin/prescriptions...")
    # Unauthenticated should fail / 401
    unauth_resp = client.get("/admin/prescriptions")
    print(f"-> Unauthenticated admin access status code: {unauth_resp.status_code} (Expected 401)")
    assert unauth_resp.status_code == 401, f"Expected 401 for unauthenticated admin access, got {unauth_resp.status_code}"

    # Log in as admin
    login_resp = client.post("/auth/admin/login", json={"password": os.environ.get("ADMIN_PASSWORD", "AdminPass123!@#")})
    assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
    
    admin_presc_resp = client.get("/admin/prescriptions")
    assert admin_presc_resp.status_code == 200, f"Admin prescriptions fetch failed: {admin_presc_resp.text}"
    admin_items = admin_presc_resp.json().get("items", [])
    print(f"-> Admin view retrieved {len(admin_items)} total prescriptions across system")
    assert any(p.get("id") == analysis_id for p in admin_items), "Created analysis missing from admin view"
    print("-> Successfully verified admin authorization & prescription monitoring!")

    print("\n=== All Task 26 E2E Verification Steps Passed! ===")

if __name__ == "__main__":
    run_e2e_verification()
