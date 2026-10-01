"""
Real End-to-End Test for Task 21: Zero-Login Secure Token-Based User Identity
Runs against live FastAPI server at http://localhost:8000
"""
import requests
import io
from PIL import Image
import sqlite3
import hashlib
import os

BASE_URL = "http://localhost:8000"
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "medical_ai.db")

def create_dummy_xray_bytes():
    img = Image.new("RGB", (224, 224), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def test_real_e2e():
    print("=== Starting Real Task 21 E2E Verification ===")
    
    # 1. First anonymous client creates session
    s1 = requests.Session()
    resp1 = s1.get(f"{BASE_URL}/auth/session")
    assert resp1.status_code == 200, f"Expected 200, got {resp1.status_code}"
    data1 = resp1.json()
    user1_id = data1.get("id") or data1.get("user", {}).get("id")
    user1_role = data1.get("role") or data1.get("user", {}).get("role")
    assert user1_id, f"User ID should be generated, got {data1}"
    assert user1_role == "USER", f"Expected USER role, got {user1_role}"
    assert "token" not in data1, "Raw token must NOT be in response body"
    assert "token_hash" not in data1, "Token hash must NOT be in response body"
    assert "user_session_token" in s1.cookies, "HttpOnly cookie user_session_token must be set"
    raw_token_1 = s1.cookies["user_session_token"]
    print(f"[PASS] Client 1 auto-provisioned anonymous user: {user1_id}")
    
    # 2. Database verification: Check SQLite stores SHA-256 hash, NOT raw token
    token_hash_1 = hashlib.sha256(raw_token_1.encode("utf-8")).hexdigest()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, role, token_hash FROM users WHERE id = ?", (user1_id,))
    row = cursor.fetchone()
    assert row is not None, "User record must exist in DB"
    assert row[1] == "USER", "DB role must be USER"
    assert row[2] == token_hash_1, "DB must store SHA-256 hash of token"
    assert raw_token_1 not in str(row), "Raw token must NOT be stored in DB"
    print(f"[PASS] DB stores SHA-256 token hash verified: {token_hash_1[:12]}...")
    
    # 3. Client 1 performs real image analysis
    img_bytes = create_dummy_xray_bytes()
    files = {"file": ("test_chest_xray.png", img_bytes, "image/png")}
    data = {"patient_id": "PT-E2E-001", "notes": "E2E Task 21 Test", "owner_user_id": "malicious-user-id"}
    
    analyze_resp = s1.post(f"{BASE_URL}/analyze", files=files, data=data)
    assert analyze_resp.status_code == 200, f"Analysis failed: {analyze_resp.text}"
    analysis_data = analyze_resp.json()
    analysis_id = analysis_data.get("analysis_id")
    assert analysis_id, "Analysis ID must be returned"
    assert "prediction" in analysis_data, "Prediction must be returned"
    assert "confidence" in analysis_data, "Confidence must be returned"
    print(f"[PASS] Real analysis completed: ID={analysis_id}, Prediction={analysis_data.get('prediction')}, Conf={analysis_data.get('confidence')}")
    
    # Verify owner_user_id in DB is user1_id (and not malicious-user-id)
    cursor.execute("SELECT owner_user_id FROM analyses WHERE analysis_id = ?", (analysis_id,))
    ana_row = cursor.fetchone()
    assert ana_row is not None, "Analysis row not found"
    assert ana_row[0] == user1_id, f"Expected owner_user_id={user1_id}, got {ana_row[0]}"
    print(f"[PASS] Analysis ownership securely bound to {user1_id}")
    
    # 4. Client 1 gets history, details, and report
    hist_resp = s1.get(f"{BASE_URL}/history")
    assert hist_resp.status_code == 200
    hist_items = hist_resp.json().get("items", [])
    assert any(item["analysis_id"] == analysis_id for item in hist_items), "Analysis should be in Client 1 history"
    print(f"[PASS] Client 1 history contains analysis {analysis_id}")
    
    detail_resp = s1.get(f"{BASE_URL}/history/{analysis_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json().get("analysis_id") == analysis_id
    print(f"[PASS] Client 1 accessed analysis details")
    
    report_resp = s1.get(f"{BASE_URL}/history/{analysis_id}/report")
    assert report_resp.status_code == 200
    assert report_resp.headers.get("content-type") == "application/pdf"
    assert len(report_resp.content) > 100
    print(f"[PASS] Client 1 downloaded PDF report ({len(report_resp.content)} bytes)")
    
    # 5. Client 2 (New Session without cookies)
    s2 = requests.Session()
    resp2 = s2.get(f"{BASE_URL}/auth/session")
    assert resp2.status_code == 200
    data2 = resp2.json()
    user2_id = data2.get("id") or data2.get("user", {}).get("id")
    assert user2_id != user1_id, "Client 2 must have distinct user ID"
    print(f"[PASS] Client 2 auto-provisioned distinct anonymous user: {user2_id}")
    
    # Client 2 attempts to read history
    hist2_resp = s2.get(f"{BASE_URL}/history")
    assert hist2_resp.status_code == 200
    hist2_items = hist2_resp.json().get("items", [])
    assert not any(item["analysis_id"] == analysis_id for item in hist2_items), "Client 2 must NOT see Client 1's history"
    print(f"[PASS] Client 2 history is isolated (0 records from Client 1)")
    
    # Client 2 attempts to access Client 1's analysis detail
    detail2_resp = s2.get(f"{BASE_URL}/history/{analysis_id}")
    assert detail2_resp.status_code in (403, 404), f"Expected 403 or 404, got {detail2_resp.status_code}"
    print(f"[PASS] Client 2 blocked from accessing Client 1 analysis ({detail2_resp.status_code})")
    
    # Client 2 attempts to access Client 1's PDF report
    report2_resp = s2.get(f"{BASE_URL}/history/{analysis_id}/report")
    assert report2_resp.status_code in (403, 404), f"Expected 403 or 404, got {report2_resp.status_code}"
    print(f"[PASS] Client 2 blocked from downloading Client 1 report ({report2_resp.status_code})")
    
    # Client 2 attempts to access Admin endpoints
    admin_probe = s2.get(f"{BASE_URL}/admin/users")
    assert admin_probe.status_code == 403, f"Expected 403 Forbidden for user accessing admin, got {admin_probe.status_code}"
    print(f"[PASS] USER token cannot access admin endpoints (403 Forbidden)")
    
    # 6. Session Reset / Logout for Client 1
    reset_resp = s1.post(f"{BASE_URL}/auth/session/reset")
    assert reset_resp.status_code == 200
    print(f"[PASS] Client 1 session reset completed")
    
    # Verify token is invalidated in DB
    cursor.execute("SELECT token_hash FROM users WHERE id = ?", (user1_id,))
    invalidated_hash = cursor.fetchone()[0]
    assert invalidated_hash is None, "Token hash in DB must be cleared after reset"
    print(f"[PASS] DB token hash cleared on reset")
    
    # Subsequent request using the invalidated cookie creates a new session
    subsequent_resp = s1.get(f"{BASE_URL}/auth/session")
    assert subsequent_resp.status_code == 200
    subsequent_data = subsequent_resp.json()
    new_user1_id = subsequent_data.get("id") or subsequent_data.get("user", {}).get("id")
    assert new_user1_id != user1_id, "New anonymous identity must be assigned after reset"
    print(f"[PASS] New anonymous identity {new_user1_id} created after reset")
    
    # 7. Admin login and verification
    admin_s = requests.Session()
    admin_login = admin_s.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": "AdminSecure2026!Clinical"},
    )
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
    admin_data = admin_login.json()
    admin_role = admin_data.get("role") or admin_data.get("user", {}).get("role")
    assert admin_role == "ADMIN", f"Expected ADMIN role, got {admin_role}"
    print(f"[PASS] Admin login succeeded")
    
    # Admin can access admin endpoints
    admin_users = admin_s.get(f"{BASE_URL}/admin/users")
    assert admin_users.status_code == 200
    print(f"[PASS] Admin accessed /admin/users")
    
    admin_analyses = admin_s.get(f"{BASE_URL}/admin/analyses")
    assert admin_analyses.status_code == 200
    print(f"[PASS] Admin accessed /admin/analyses")
    
    admin_system = admin_s.get(f"{BASE_URL}/admin/system")
    assert admin_system.status_code == 200
    print(f"[PASS] Admin accessed /admin/system")
    
    conn.close()
    print("\n=======================================================")
    print("ALL REAL TASK 21 END-TO-END CHECKS PASSED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    test_real_e2e()
