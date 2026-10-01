import os
import sys
import requests
import sqlite3

BASE_URL = "http://localhost:8000"
DB_PATH = os.path.join(os.path.dirname(__file__), "backend", "data", "medical_ai.db")
SAMPLE_XRAY = os.path.join(os.path.dirname(__file__), "data", "chest_xray", "test", "NORMAL", "IM-0001-0001.jpeg")

def main():
    print("=== TASK 20 REAL USER WORKFLOW & CROSS-USER ISOLATION VERIFICATION ===")
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
    from api.auth import hash_password
    from database.database import create_user, get_user_by_username, get_db_connection
    
    # Ensure Alice and Bob exist
    alice = get_user_by_username("doctor_alice")
    if not alice:
        alice = create_user("doctor_alice", hash_password("AliceSecurePass123!"), role="USER")
    else:
        conn = get_db_connection()
        conn.execute("UPDATE users SET password_hash = ?, is_active = 1 WHERE username = 'doctor_alice'", (hash_password("AliceSecurePass123!"),))
        conn.commit()
        conn.close()
        alice = get_user_by_username("doctor_alice")

    bob = get_user_by_username("doctor_bob")
    if not bob:
        bob = create_user("doctor_bob", hash_password("BobSecurePass123!"), role="USER")
    else:
        conn = get_db_connection()
        conn.execute("UPDATE users SET password_hash = ?, is_active = 1 WHERE username = 'doctor_bob'", (hash_password("BobSecurePass123!"),))
        conn.commit()
        conn.close()
        bob = get_user_by_username("doctor_bob")

    alice_id = alice["id"]
    bob_id = bob["id"]
    print(f"[OK] Doctor Alice prepared: ID={alice_id}, Role={alice['role']}")
    print(f"[OK] Doctor Bob prepared: ID={bob_id}, Role={bob['role']}")

    # 2. Login as Doctor Alice
    session_alice = requests.Session()
    login_resp = session_alice.post(f"{BASE_URL}/auth/login", json={"username": "doctor_alice", "password": "AliceSecurePass123!"})
    assert login_resp.status_code == 200, f"Alice login failed: {login_resp.text}"
    alice_data = login_resp.json()
    assert alice_data["user"]["role"] == "USER"
    print("[PASS] Step 1: Doctor Alice login successful, role=USER")

    # 3. Verify /auth/me for Alice
    me_resp = session_alice.get(f"{BASE_URL}/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "doctor_alice"
    assert me_resp.json()["role"] == "USER"
    print("[PASS] Step 2: Doctor Alice /auth/me confirmed")

    # 4. Upload real chest X-ray as Alice
    assert os.path.exists(SAMPLE_XRAY), f"Sample X-ray not found at {SAMPLE_XRAY}"
    with open(SAMPLE_XRAY, "rb") as img_file:
        files = {"file": ("chest_xray_normal.jpeg", img_file, "image/jpeg")}
        analyze_resp = session_alice.post(f"{BASE_URL}/analyze", files=files)
    
    assert analyze_resp.status_code == 200, f"Analysis failed: {analyze_resp.text}"
    analysis = analyze_resp.json()
    analysis_id = analysis["analysis_id"]
    print(f"[PASS] Step 3: Analysis complete! ID={analysis_id}, Prediction={analysis.get('prediction')}, Confidence={analysis.get('confidence')}")

    # 5. Check SQLite database ownership
    from database.database import get_analysis_by_id
    stored = get_analysis_by_id(analysis_id)
    assert stored is not None, "Analysis not saved to database!"
    assert stored.get("owner_user_id") == alice_id, f"Owner mismatch! Expected {alice_id}, got {stored.get('owner_user_id')}"
    print(f"[PASS] Step 4: Server-side ownership strictly verified in SQLite: owner_user_id={stored.get('owner_user_id')} (Alice)")

    # 6. Alice checks history
    hist_resp = session_alice.get(f"{BASE_URL}/history")
    assert hist_resp.status_code == 200
    alice_history = hist_resp.json().get("items", [])
    alice_ids = [item["analysis_id"] for item in alice_history]
    assert analysis_id in alice_ids, f"Alice cannot find her own analysis {analysis_id} in history! Found: {alice_ids}"
    print(f"[PASS] Step 5: Alice history returned {len(alice_history)} records, including {analysis_id}")

    # 7. Alice gets analysis details
    detail_resp = session_alice.get(f"{BASE_URL}/history/{analysis_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["analysis_id"] == analysis_id
    print("[PASS] Step 6: Alice successfully retrieved analysis details")

    # 8. Alice downloads PDF report
    report_resp = session_alice.get(f"{BASE_URL}/history/{analysis_id}/report")
    assert report_resp.status_code == 200
    assert report_resp.content.startswith(b"%PDF"), "Report is not a valid PDF!"
    print(f"[PASS] Step 7: Alice successfully downloaded PDF report ({len(report_resp.content)} bytes)")

    # 9. Login as Doctor Bob (User B)
    session_bob = requests.Session()
    login_bob_resp = session_bob.post(f"{BASE_URL}/auth/login", json={"username": "doctor_bob", "password": "BobSecurePass123!"})
    assert login_bob_resp.status_code == 200
    print("[PASS] Step 8: Doctor Bob login successful, role=USER")

    # 10. Bob queries history -> Must NOT see Alice's analysis
    bob_hist_resp = session_bob.get(f"{BASE_URL}/history")
    assert bob_hist_resp.status_code == 200
    bob_history = bob_hist_resp.json().get("items", [])
    bob_ids = [item["analysis_id"] for item in bob_history]
    assert analysis_id not in bob_ids, f"CROSS-USER SECURITY VIOLATION: Bob can see Alice's analysis {analysis_id}!"
    print(f"[PASS] Step 9: Bob history isolated: {len(bob_history)} analyses, Alice's analysis NOT visible")

    # 11. Bob attempts to access Alice's analysis details -> Must be 403 / 404
    bob_detail_resp = session_bob.get(f"{BASE_URL}/history/{analysis_id}")
    assert bob_detail_resp.status_code in [403, 404], f"CROSS-USER VIOLATION: Bob got status {bob_detail_resp.status_code} for Alice's record"
    print(f"[PASS] Step 10: Bob access to Alice analysis detail blocked (Status {bob_detail_resp.status_code})")

    # 12. Bob attempts to download Alice's PDF report -> Must be 403 / 404
    bob_report_resp = session_bob.get(f"{BASE_URL}/history/{analysis_id}/report")
    assert bob_report_resp.status_code in [403, 404], f"CROSS-USER VIOLATION: Bob downloaded Alice's report! Status {bob_report_resp.status_code}"
    print(f"[PASS] Step 11: Bob access to Alice report blocked (Status {bob_report_resp.status_code})")

    # 13. Bob attempts to access Admin endpoints -> 403 Forbidden
    for endpoint in ["/admin/statistics", "/admin/users", "/admin/analyses", "/admin/system"]:
        admin_resp = session_bob.get(f"{BASE_URL}{endpoint}")
        assert admin_resp.status_code == 403, f"RBAC VIOLATION: Bob accessed {endpoint}! Status: {admin_resp.status_code}"
    print("[PASS] Step 12: USER role strictly forbidden from all /admin/* endpoints")

    # 14. Admin access verification
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    admin_hash = hash_password("AdminPass123456!")
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (admin_hash,))
    conn.commit()
    conn.close()

    session_admin = requests.Session()
    admin_login_resp = session_admin.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "AdminPass123456!"})
    assert admin_login_resp.status_code == 200
    print("[PASS] Step 13: Admin login successful")

    admin_detail_resp = session_admin.get(f"{BASE_URL}/history/{analysis_id}")
    assert admin_detail_resp.status_code == 200, "Admin should be able to view all analyses"
    print("[PASS] Step 14: Admin can view Alice's analysis")

    admin_stats_resp = session_admin.get(f"{BASE_URL}/admin/statistics")
    assert admin_stats_resp.status_code == 200
    print("[PASS] Step 15: Admin can access /admin/statistics")

    # 15. Alice Logout
    logout_resp = session_alice.post(f"{BASE_URL}/auth/logout")
    assert logout_resp.status_code == 200
    alice_after_logout = session_alice.get(f"{BASE_URL}/auth/me")
    assert alice_after_logout.status_code == 401
    print("[PASS] Step 16: Alice logout cleared session, /auth/me returns 401")

    print("\n=======================================================")
    print("ALL REAL USER & CROSS-USER SECURITY TESTS PASSED 100%!")
    print("=======================================================")

if __name__ == "__main__":
    main()
